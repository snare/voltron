#!/bin/bash
#
# Install Voltron for whichever debuggers are detected (only GDB and LLDB so
# far).
#
# Adapted from pwndbg's install script.
#
# Usage: ./install.sh [ -u -d ] [ -b BACKEND ]
#   -u      Install to user's site-packages directory
#   -d      Install in developer mode (-e flag passed to pip)
#   -b      Select backend ("", "gdb", "lldb", or "gdb,lldb") to install for
SUDO='sudo'
GDB=$(command -v gdb)
LLDB=$(command -v lldb)
APT_GET=$(command -v apt-get)
YUM_YUM=$(command -v yum)
YUM_DNF=$(command -v dnf)

[[ -z "${GDB}" ]]
BACKEND_GDB=$?
[[ -z "${LLDB}" ]]
BACKEND_LLDB=$?

set -x

if [ -z "${LLDB}" ]; then
    for i in `seq 6 8`; do
        LLDB=$(command -v lldb-3.$i)
        if [ -n "${LLDB}" ]; then
            break
        fi
    done
fi

while getopts ":udsb:" opt; do
  case $opt in
    u)
      USER_MODE='--user'
      SUDO=''
      ;;
    d)
      DEV_MODE="-e"
      ;;
    s)
      SKIP_UPDATE='-s'
      ;;
    b)
      [[ ! "${OPTARG}" =~ "gdb" ]]
      BACKEND_GDB=$?
      
      [[ ! "${OPTARG}" =~ "lldb" ]]
      BACKEND_LLDB=$?
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done

if [ "${BACKEND_GDB}" -eq 1 ] && [ -z "${GDB}" ]; then
    echo "Requested to install voltron for gdb, but gdb not present on the system"
    exit 1
fi
if [ "${BACKEND_LLDB}" -eq 1 ] && [ -z "${LLDB}" ]; then
    echo "Requested to install voltron for lldb, but lldb not present on the system"
    exit 1
fi


set -e

function install_apt {
    if [ -n "${APT_GET}" ]; then
        if [ -z "${SKIP_UPDATE}" ]; then
            sudo apt-get update
        fi
        if echo $PYVER|grep "3\."; then
            sudo apt-get -y install libreadline6-dev python3-dev python3-setuptools python3-yaml python3-pip
        else
            sudo apt-get -y install libreadline6-dev python-dev python-setuptools python-yaml python-pip
        fi
    fi
}

function install_yum {
    local CMD=""
    if [ -n "${YUM_DNF}" ]; then
        CMD=$YUM_DNF
    else
        if [ -n "${YUM_YUM}" ]; then
            CMD=$YUM_YUM
	fi
    fi

    if [ "${CMD}" != "" ]; then
        local PARAMS="--assumeyes"
        if [ -z "${SKIP_UPDATE}" ]; then
            PARAMS="$PARAMS --refresh"
        fi

        if echo $PYVER|grep "3\."; then
            sudo $CMD $PARAMS install readline-devel python3-devel python3-setuptools python3-yaml python3-pip
        else
            sudo $CMD $PARAMS install readline-devel python-devel python-setuptools python-yaml python-pip
        fi
    fi
}

function install_packages {
    install_apt
    install_yum
}


if [ "${BACKEND_GDB}" -eq 1 ]; then
    # Find the Python version used by GDB
    GDB_PYVER=$(${GDB} -batch -q --nx -ex 'pi import platform; print(".".join(platform.python_version_tuple()[:2]))')
    GDB_PYTHON=$(${GDB} -batch -q --nx -ex 'pi import sys; print(sys.executable)')
    GDB_PYTHON="${GDB_PYTHON/%$GDB_PYVER/}${GDB_PYVER}"

    install_packages

    if [ -z $USER_MODE ]; then
        GDB_SITE_PACKAGES=$(${GDB} -batch -q --nx -ex 'pi import site; print(site.getsitepackages()[0])')
    else
        GDB_SITE_PACKAGES=$(${GDB} -batch -q --nx -ex 'pi import site; print(site.getusersitepackages())')
    fi

    # Install Voltron and dependencies
    ${SUDO} ${GDB_PYTHON} -m pip install -U $USER_MODE $DEV_MODE .

    # Add Voltron to gdbinit
    GDB_INIT_FILE="${HOME}/.gdbinit"
    if [ -e ${GDB_INIT_FILE} ]; then
        sed -i.bak '/voltron/d' ${GDB_INIT_FILE}
    fi

    if [ -z $DEV_MODE ]; then
        GDB_ENTRY_FILE="$GDB_SITE_PACKAGES/voltron/entry.py"
    else
        GDB_ENTRY_FILE="$(pwd)/voltron/entry.py"
    fi
    echo "source $GDB_ENTRY_FILE" >> ${GDB_INIT_FILE}
fi

if [ "${BACKEND_LLDB}" -eq 1 ]; then
    # Find the Python version used by LLDB
    LLDB_PYVER=$(${LLDB} -Qxb --one-line 'script import platform; print(".".join(platform.python_version_tuple()[:2]))'|tail -1)
    LLDB_PYTHON=$(${LLDB} -Qxb --one-line 'script import sys; print(sys.executable)'|tail -1)
    LLDB_PYTHON="${LLDB_PYTHON/%$LLDB_PYVER/}${LLDB_PYVER}"
    if [ -z $USER_MODE ]; then
        LLDB_SITE_PACKAGES=$(${LLDB} -Qxb --one-line 'script import site; print(site.getsitepackages()[0])'|tail -1)
    else
        LLDB_SITE_PACKAGES=$(${LLDB} -Qxb --one-line 'script import site; print(site.getusersitepackages())'|tail -1)
    fi

    install_packages

    if [ "$LLDB_SITE_PACKAGES" == "$GDB_SITE_PACKAGES" ]; then
        echo "Skipping installation for LLDB - same site-packages directory"
    else
        # Install Voltron and dependencies
        ${SUDO} ${LLDB_PYTHON} -m pip install -U $USER_MODE $DEV_MODE .
    fi

    # Add Voltron to lldbinit
    LLDB_INIT_FILE="${HOME}/.lldbinit"
    if [ -e ${LLDB_INIT_FILE} ]; then
        sed -i.bak '/voltron/d' ${LLDB_INIT_FILE}
    fi

    if [ -z $DEV_MODE ]; then
        LLDB_ENTRY_FILE="$LLDB_SITE_PACKAGES/voltron/entry.py"
    else
        LLDB_ENTRY_FILE="$(pwd)/voltron/entry.py"
    fi
    echo "command script import $LLDB_ENTRY_FILE" >> ${LLDB_INIT_FILE}
fi

if [ "${BACKEND_GDB}" -ne 1 ] && [ "${BACKEND_LLDB}" -ne 1 ]; then
    # Find system Python
    PYTHON=$(command -v python)
    PYVER=$(${PYTHON} -c 'import platform; print(".".join(platform.python_version_tuple()[:2]))')
    if [ -z $USER_MODE ]; then
        PYTHON_SITE_PACKAGES=$(${PYTHON} -c 'import site; print(site.getsitepackages()[0])')
    else
        PYTHON_SITE_PACKAGES=$(${PYTHON} -c 'import site; print(site.getusersitepackages())')
    fi

    install_packages

    # Install Voltron and dependencies
    ${SUDO} ${PYTHON} -m pip install -U $USER_MODE $DEV_MODE .
fi

set +x
echo "=============================================================="
if [ "${BACKEND_GDB}" -eq 1 ]; then
    echo "Installed for GDB (${GDB}):"
    echo "  Python:             $GDB_PYTHON"
    echo "  Packages directory: $GDB_SITE_PACKAGES"
    echo "  Added voltron to:   $GDB_INIT_FILE"
    echo "  Entry point:        $GDB_ENTRY_FILE"
fi
if [ "${BACKEND_LLDB}" -eq 1 ]; then
    echo "Installed for LLDB (${LLDB}):"
    echo "  Python:             $LLDB_PYTHON"
    echo "  Packages directory: $LLDB_SITE_PACKAGES"
    echo "  Added voltron to:   $LLDB_INIT_FILE"
    echo "  Entry point:        $LLDB_ENTRY_FILE"
fi
if [ "${BACKEND_GDB}" -ne 1 ] && [ "${BACKEND_LLDB}" -ne 1 ]; then
    if [ -z "${GDB}" ] && [ -z "${LLDB}" ]; then
        echo -n "Couldn't find any debuggers. "
    else
        echo -n "No debuggers selected. "
    fi

    echo "Installed using the Python in your path:"
    echo "  Python:             $PYTHON"
    echo "  Packages directory: $PYTHON_SITE_PACKAGES"
    echo "  Did not add Voltron to any debugger init files."
fi
