#!/usr/bin/env bash

COLOR_ERROR='\033[0;31m'
COLOR_SUCCESS='\033[0;32m'
COLOR_WARNING='\033[1;33m'
COLOR_INFO='\033[0;34m'
COLOR_RESET='\033[0m'

print_error() {
  echo -e "${COLOR_ERROR}[ERROR]${COLOR_RESET} $1"
}

print_success() {
  echo -e "${COLOR_SUCCESS}[SUCCESS]${COLOR_RESET} $1"
}

print_warning() {
  echo -e "${COLOR_WARNING}[WARNING]${COLOR_RESET} $1"
}

print_info() {
  echo -e "${COLOR_INFO}[INFO]${COLOR_RESET} $1"
}

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}
