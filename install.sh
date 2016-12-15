#!/bin/bash
#
# Install Voltron for whichever debuggers are detected (only GDB and LLDB so
# far).
#
# Adapted from pwndbg's install script.
#
# Usage: ./install.sh [ -u -d ]
#   -u      Install to user's site-packages directory
#   -d      Install in developer mode (-e flag passed to pip)
#
SUDO='sudo'
GDB=$(command -v gdb)
LLDB=$(command -v lldb)
APT_GET=$(command -v apt-get)

set -x

if [ -z "${LLDB}" ]; then
    for i in `seq 6 8`; do
        LLDB=$(command -v lldb-3.$i)
        if [ -n "${LLDB}" ]; then
            break
        fi
    done
fi

while getopts ":uds" opt; do
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
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done

set -e

function install_apt() {
    PYVER=$1
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

if [ -n "${GDB}" ]; then
    # Find the Python version used by GDB
    GDB_PYVER=$(${GDB} -batch -q --nx -ex 'pi import platform; print(".".join(platform.python_version_tuple()[:2]))')
    GDB_PYTHON=$(${GDB} -batch -q --nx -ex 'pi import sys; print(sys.executable)')
    GDB_PYTHON="${GDB_PYTHON}${GDB_PYVER}"

    install_apt($GDB_PYVER)

    if [ -z $USER_MODE ]; then
        GDB_SITE_PACKAGES=$(${GDB} -batch -q --nx -ex 'pi import site; print(site.getsitepackages()[0])')
    else
        GDB_SITE_PACKAGES=$(${GDB} -batch -q --nx -ex 'pi import site; print(site.getusersitepackages())')
    fi

    # Install Voltron and dependencies
    ${SUDO} ${GDB_PYTHON} -m pip install -U $USER_MODE $DEV_MODE .

    # Add Voltron to gdbinit
    GDB_INIT_FILE="${HOME}/.gdbinit"
    sed -i.bak '/voltron/d' ${GDB_INIT_FILE}
    if [ -z $DEV_MODE ]; then
        GDB_ENTRY_FILE="$GDB_SITE_PACKAGES/voltron/entry.py"
    else
        GDB_ENTRY_FILE="$(pwd)/voltron/entry.py"
    fi
    echo "source $GDB_ENTRY_FILE" >> ${GDB_INIT_FILE}
fi

if [ -n "${LLDB}" ]; then
    # Find the Python version used by LLDB
    LLDB_PYVER=$(${LLDB} -Qxb --one-line 'script import platform; print(".".join(platform.python_version_tuple()[:2]))'|tail -1)
    LLDB_PYTHON=$(${LLDB} -Qxb --one-line 'script import sys; print(sys.executable)'|tail -1)
    LLDB_PYTHON="${LLDB_PYTHON}${LLDB_PYVER}"
    if [ -z $USER_MODE ]; then
        LLDB_SITE_PACKAGES=$(${LLDB} -Qxb --one-line 'script import site; print(site.getsitepackages()[0])'|tail -1)
    else
        LLDB_SITE_PACKAGES=$(${LLDB} -Qxb --one-line 'script import site; print(site.getusersitepackages())'|tail -1)
    fi

    install_apt($LLDB_PYVER)

    if [ "$LLDB_SITE_PACKAGES" == "$GDB_SITE_PACKAGES" ]; then
        echo "Skipping installation for LLDB - same site-packages directory"
    else
        # Install Voltron and dependencies
        ${SUDO} ${LLDB_PYTHON} -m pip install -U $USER_MODE $DEV_MODE .
    fi

    # Add Voltron to lldbinit
    LLDB_INIT_FILE="${HOME}/.lldbinit"
    sed -i.bak '/voltron/d' ${LLDB_INIT_FILE}
    if [ -z $DEV_MODE ]; then
        LLDB_ENTRY_FILE="$LLDB_SITE_PACKAGES/voltron/entry.py"
    else
        LLDB_ENTRY_FILE="$(pwd)/voltron/entry.py"
    fi
    echo "command script import $LLDB_ENTRY_FILE" >> ${LLDB_INIT_FILE}
fi

if [ -z "${GDB}" ] && [ -z "${LLDB}" ]; then
    # Find system Python
    PYTHON=$(command -v python)
    PYVER=$(${PYTHON} -c 'import platform; print(".".join(platform.python_version_tuple()[:2]))')
    if [ -z $USER_MODE ]; then
        PYTHON_SITE_PACKAGES=$(${PYTHON} -c 'import site; print(site.getsitepackages()[0])')
    else
        PYTHON_SITE_PACKAGES=$(${PYTHON} -c 'import site; print(site.getusersitepackages())')
    fi

    install_apt($PYVER)

    # Install Voltron and dependencies
    ${SUDO} ${PYTHON} -m pip install -U $USER_MODE $DEV_MODE .
fi

set +x
echo "=============================================================="
if [ -n "${GDB}" ]; then
    echo "Installed for GDB (${GDB}):"
    echo "  Python:             $GDB_PYTHON"
    echo "  Packages directory: $GDB_SITE_PACKAGES"
    echo "  Added voltron to:   $GDB_INIT_FILE"
    echo "  Entry point:        $GDB_ENTRY_FILE"
fi
if [ -n "${LLDB}" ]; then
    echo "Installed for LLDB (${LLDB}):"
    echo "  Python:             $LLDB_PYTHON"
    echo "  Packages directory: $LLDB_SITE_PACKAGES"
    echo "  Added voltron to:   $LLDB_INIT_FILE"
    echo "  Entry point:        $LLDB_ENTRY_FILE"
fi
if [ -z "${GDB}" ] && [ -z "${LLDB}" ]; then
    echo "Couldn't find any debuggers. Installed using the Python in your path:"
    echo "  Python:             $PYTHON"
    echo "  Packages directory: $PYTHON_SITE_PACKAGES"
    echo "  Did not add Voltron to any debugger init files."
fi
