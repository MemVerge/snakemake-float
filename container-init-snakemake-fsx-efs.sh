#!/bin/bash
#
# This script will be submitted as a contianerInit hook script and do following things:
#
# - Install snakemake and its dependencies including snakemake-float
# - If running as admin, a snakemake user is added and the user directory is placed under /home directory.
# - Running as admin can cause Snakemake to fail with permission denied errors.
# - Running as a non-admin user will create a user with the same UID as the MM Cloud user.
#
# Following parameters can be passed in as environment variables:
#
# OPCENTER_PASSWORD_SECRET: The name of the OPCentre secret passed as '{secret:<Secret name>}'.
# SNAKEMAKE_VERSION: The version of Snakemake to be installed. Default is 7.32.4.
# SNAKEMAKE_FLOAT_VERSION: The version of snakemake-float to be installed.
# Default is MemVerge/snakemake-float/archive/refs/tags/v0.2.0.tar.gz

#set -x
OPCENTER_PASSWORD_SECRET=${OPCENTER_PASSWORD_SECRET:-'{secret:OPCENTER_PASSWORD}'}
SNAKEMAKE_VERSION=${SNAKEMAKE_VERSION:-'7.32.4'}
SNAKEMAKE_FLOAT_VERSION=${SNAKEMAKE_FLOAT_VERSION:-'MemVerge/snakemake-float/archive/refs/tags/v0.2.0.tar.gz'}

export PATH=$PATH:/usr/bin:/usr/local/bin:/opt/memverge/bin
export HOME=/root
export HOME_DIR="/home"
export SMK_ROOT_HOME="$HOME_DIR/snakemake"

LOG_FILE=$FLOAT_JOB_PATH/container-init.log
touch $LOG_FILE
exec >$LOG_FILE 2>&1

function log() {
  if [[ -f ${LOG_FILE_PATH} ]]; then
    echo $(date): "$@" >>${LOG_FILE_PATH}
  fi
  echo $(date): "$@"
}

function error() {
  log "[ERROR] $1"
}

function die() {
  error "$1"
  podman kill -a 2>&1 >/dev/null
  exit 1
}

function trim_quotes() {
  : "${1//\'/}"
  printf '%s\n' "${_//\"/}"
}

function assure_root() {
  if [[ ${EUID} -ne 0 ]]; then
    die "Please run with root or sudo privilege."
  fi
}

function echolower {
  tr [:upper:] [:lower:] <<<"${*}"
}

function get_secret {
  input_string=$1

  pattern='^\{secret:(.*)\}$'

  if [[ $input_string =~ $pattern ]]; then
    # Matched, return the secret name string
    matched_string="${BASH_REMATCH[1]}"
    secret_value=$(float secret get $matched_string -a $FLOAT_ADDR)
    if [[ $? -eq 0 ]]; then
      # Have this secret, will use the secret value
      echo $secret_value
      return
    else
      # Don't have this secret, will still use the input string
      echo $1
    fi
  else
    # Not matched, return the input string
    echo $1
  fi
}

function set_secret {
  file_name=$1
  secret_name=${FLOAT_JOB_ID}_SSHKEY
  float secret set $secret_name --file $file_name -a $FLOAT_ADDR
  if [[ $? -ne 0 ]]; then
    die "Set secret $secret_name failed"
  fi
}

function prepare_git_env() {
  git_path=$(which git)
  if [[ $? -eq 0 ]]; then
    log "Git is already installed at $git_path"
    return
  fi
  log "Install git"
  yum install -y --quiet git
  if [[ $? -ne 0 ]]; then
    die "Install git failed"
  fi
}

function prepare_tmux_env() {
  tmux_path=$(which tmux)
  if [[ $? -eq 0 ]]; then
    log "Tmux is already installed at $tmux_path"
    return
  fi
  log "Install Tmux"
  yum install -y --quiet tmux
  if [[ $? -ne 0 ]]; then
    die "Install Tmux failed"
  fi
}

function prepare_user_env {
  if [[ $FLOAT_USER_ID -eq 0 ]]; then
    /usr/sbin/useradd -m -d $SMK_ROOT_HOME -s /bin/bash snakemake
    su - snakemake -c "ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa > /dev/null"
    su - snakemake -c "mv ~/.ssh/id_rsa.pub ~/.ssh/authorized_keys"
    set_secret $SMK_ROOT_HOME/.ssh/id_rsa
    rm -f $SMK_ROOT_HOME/.ssh/id_rsa
    USER_PROFILE=$SMK_ROOT_HOME/.bash_profile
    echo "snakemake ALL=(ALL:ALL) NOPASSWD: ALL" | tee -a /etc/sudoers.d/snakemake
  else
    systemctl stop munge
    /usr/sbin/userdel slurm
    /usr/sbin/userdel munge
    id $FLOAT_USER_ID > /dev/null 2>&1
    if [[ $? -eq 0 ]]; then
      old_name=`getent passwd $FLOAT_USER_ID | cut -d: -f1`
      /usr/sbin/userdel $old_name
    fi
    FLOAT_USER_HOME="$HOME_DIR/$FLOAT_USER"
    /usr/sbin/useradd -u $FLOAT_USER_ID -m -d $FLOAT_USER_HOME -s /bin/bash $FLOAT_USER
    su - $FLOAT_USER -c "ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa > /dev/null"
    su - $FLOAT_USER -c "mv ~/.ssh/id_rsa.pub ~/.ssh/authorized_keys"
    set_secret $FLOAT_USER_HOME/.ssh/id_rsa
    rm -f $FLOAT_USER_HOME/.ssh/id_rsa
    USER_PROFILE=$FLOAT_USER_HOME/.bash_profile
  fi
}

function install_conda() {
  conda_path=$(which conda)
  if [[ $? -eq 0 ]]; then
    log "Conda is already installed at $conda_path"
    return
  fi
  log "Install Conda"
  if [[ $FLOAT_USER_ID -eq 0 ]]; then
    cd $SMK_ROOT_HOME
    mkdir -p $SMK_ROOT_HOME/miniconda3
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O $SMK_ROOT_HOME/miniconda3/miniconda.sh > /dev/null 2>&1
    bash $SMK_ROOT_HOME/miniconda3/miniconda.sh -b -u -p $SMK_ROOT_HOME/miniconda3 > /dev/null 2>&1
    rm $SMK_ROOT_HOME/miniconda3/miniconda.sh
    source $SMK_ROOT_HOME/miniconda3/bin/activate
    conda init --all
  else
    su - $FLOAT_USER -c "
      mkdir -p $FLOAT_USER_HOME/miniconda3 &&
      wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O $FLOAT_USER_HOME/miniconda3/miniconda.sh > /dev/null 2>&1 &&
      bash $FLOAT_USER_HOME/miniconda3/miniconda.sh -b -u -p $FLOAT_USER_HOME/miniconda3 > /dev/null 2>&1 &&
      rm $FLOAT_USER_HOME/miniconda3/miniconda.sh &&
      $FLOAT_USER_HOME/miniconda3/bin/conda init --all
    "
  fi
}

function install_snakemake() {
  export PATH=$PATH:/usr/bin
  smk_path=$(which snakemake)
  if [[ $? -eq 0 ]]; then
    log "Snakemake is already installed at $smk_path"
    return
  fi
  log "Install Snakemake"
  if [[ $FLOAT_USER_ID -eq 0 ]]; then
    conda create --quiet -y -c conda-forge -c bioconda -n snakemake bioconda::snakemake==$SNAKEMAKE_VERSION
    echo "conda activate snakemake" >> $SMK_ROOT_HOME/.bashrc
  else
    su - $FLOAT_USER -c "conda create --quiet -y -c conda-forge -c bioconda -n snakemake bioconda::snakemake==$SNAKEMAKE_VERSION"
    echo "conda activate snakemake" >> $FLOAT_USER_HOME/.bashrc
  fi
}

function install_snakemake_float() {
  log "Install snakemake-float"
  if [[ $FLOAT_USER_ID -eq 0 ]]; then
    cd $SMK_ROOT_HOME
    curl -LJO https://github.com/$SNAKEMAKE_FLOAT_VERSION > /dev/null 2>&1
    mkdir -p "$SMK_ROOT_HOME/.config/snakemake/snakemake-float"
    tar -xvf snakemake-float*tar.gz -C $SMK_ROOT_HOME/.config/snakemake/snakemake-float/ --strip-components=1
    rm snakemake-float*tar.gz
  else
    su $FLOAT_USER -c "
      cd $FLOAT_USER_HOME &&
      curl -LJO https://github.com/$SNAKEMAKE_FLOAT_VERSION > /dev/null 2>&1 &&
      mkdir -p $FLOAT_USER_HOME/.config/snakemake/snakemake-float &&
      tar -xvf snakemake-float*tar.gz -C $FLOAT_USER_HOME/.config/snakemake/snakemake-float/ --strip-components=1 &&
      rm snakemake-float*tar.gz
    "
  fi
}

function login_to_mmc {
  log "Login to MMC"
  if [[ $FLOAT_USER_ID -eq 0 ]]; then
    log "su - snakemake -c float login -a $FLOAT_ADDR -u $FLOAT_USER -p ****"
    su - snakemake -c "float login -a $FLOAT_ADDR -u $FLOAT_USER -p $(get_secret $OPCENTER_PASSWORD_SECRET)"
  else
    log "su - $FLOAT_USER -c float login -a $FLOAT_ADDR -u $FLOAT_USER -p ****"
    su - $FLOAT_USER -c "float login -a $FLOAT_ADDR -u $FLOAT_USER -p $(get_secret $OPCENTER_PASSWORD_SECRET)"
  fi
}

#env

# Execute setup scripts
assure_root

prepare_tmux_env
prepare_git_env
prepare_user_env

install_conda
install_snakemake
install_snakemake_float

login_to_mmc

exit 0
