#!/bin/bash
#
# Install Voltron for whichever debuggers are detected (only GDB and LLDB so
# far).
#

function usage {
    cat <<END
Voltron installer script.

This script will attempt to find GDB/LLDB, infer the correct Python to use, and
install Voltron. By default it will attempt to detect a single version of each
GDB  and LLDB, and will install into the user's site-packages directory. The
options below can be used to change this behaviour.

Usage: ./install.sh [ -s -d -S ] [ -v virtualenv ] [ -b BACKEND ]
  -s            Install to system's site-packages directory
  -d            Install in developer mode (-e flag passed to pip)
  -v venv       Install into a virtualenv (only for LLDB)
  -b debugger   Select debugger backend ("", "gdb", "lldb", or "gdb,lldb") for
                which to install
  -S            Skip package manager (apt/yum) update
END
    exit 1
}

GDB=$(command -v gdb)
LLDB=$(command -v lldb)
APT_GET=$(command -v apt-get)
YUM_YUM=$(command -v yum)
YUM_DNF=$(command -v dnf)

# Default to --user install without sudo
USER_MODE='--user'
SUDO=''

[[ -z "${GDB}" ]]
BACKEND_GDB=$?
[[ -z "${LLDB}" ]]
BACKEND_LLDB=$?

if [ -z "${LLDB}" ]; then
    for i in `seq 6 8`; do
        LLDB=$(command -v lldb-3.$i)
        if [ -n "${LLDB}" ]; then
            break
        fi
    done
fi

while getopts ":dsSb:v:" opt; do
  case $opt in
    s)
      USER_MODE=''
      SUDO=$(command -v sudo)
      ;;
    d)
      DEV_MODE="-e"
      ;;
    v)
      VENV="${OPTARG}"
      USER_MODE=''
      SUDO=''
      ;;
    S)
      SKIP_UPDATE='-s'
      ;;
    b)
      [[ ! "${OPTARG}" =~ "gdb" ]]
      BACKEND_GDB=$?
      
      [[ ! "${OPTARG}" =~ "lldb" ]]
      BACKEND_LLDB=$?
      ;;
    \?)
      usage
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

set -ex

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

function get_lldb_python_exe {
    # Find the Python version used by LLDB
    local lldb_pyver=$(${LLDB} -Q -x -b --one-line 'script import platform; print(".".join(platform.python_version_tuple()[:2]))'|tail -1)
    local lldb_python=$(${LLDB} -Q -x -b --one-line 'script import sys; print(sys.executable)'|tail -1)
    
    lldb_python=$(${LLDB} -Q -x -b --one-line 'script import sys; print(sys.executable)'|tail -1)
    local lldb_python_basename=$(basename "${lldb_python}")
    if [ "python" = "$lldb_python_basename" ];
    then
        lldb_python="${lldb_python/%$lldb_pyver/}${lldb_pyver}"
    elif [ "lldb" = "$lldb_python_basename" ];
    then
        # newer lldb versions report sys.path as /path/to/lldb instead of python
        # sys.exec_path still appears to be the parent path of bin/python though
        local lldb_python_exec_prefix=$(${LLDB} -Q -x -b --one-line 'script import sys; print(sys.exec_prefix)'|tail -1)
        lldb_python="$lldb_python_exec_prefix/bin/python"
        lldb_python="${lldb_python/%$lldb_pyver/}${lldb_pyver}"
    fi

    echo "$lldb_python"

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

    ${LLDB_PYTHON} -m pip install --user --upgrade six    

    if [ -n "${VENV}" ]; then
        echo "Creating virtualenv..."
        ${LLDB_PYTHON} -m pip install --user virtualenv
        ${LLDB_PYTHON} -m virtualenv "${VENV}"
        LLDB_PYTHON="${VENV}/bin/python"
        LLDB_SITE_PACKAGES=$(find "${VENV}" -name site-packages)
    elif [ -z "${USER_MODE}" ]; then
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

    if [ -z "${DEV_MODE}" ]; then
        LLDB_ENTRY_FILE="$LLDB_SITE_PACKAGES/voltron/entry.py"
    else
        LLDB_ENTRY_FILE="$(pwd)/voltron/entry.py"
    fi

    if [ -n "${VENV}" ]; then
        echo "script import sys;sys.path.append('${LLDB_SITE_PACKAGES}')" >> ${LLDB_INIT_FILE}
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
