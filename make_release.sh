#!/bin/bash

#set -x
set -o errexit
set -o nounset

PackageName="seal-galaxy"

function rewrite_seal_version() {
	local seal_rev="${1}"
	local short_rev="${seal_rev::8}"
	local version_str="master_${short_rev}"
	echo "Will rewrite tool_dependencies.xml setting the the package version to '${version_str}'."
	echo "Are you sure you want to proceed? [Y/n]"
	read -p "Answer: " yn
	case "${yn}" in
			''|[Yy]) # do nothing and keep going
					;;
			[Nn]) echo "Aborting"; exit 0
					;;
			*) usage_error "Unrecognized answer. Please specify Y or n"
					;;
	esac

	local grep_expr='<package name="seal" version=".*">'
	if ! grep  "${grep_expr}" tool_dependencies.xml >/dev/null ; then
			error "Couldn't find expected package line in tool_dependencies.xml"
	fi

	printf -v sed_expr1  '/<package name="seal"/s/version="[^"]*"/version="%s"/' "${version_str}"
	printf -v sed_expr2  '/<action type="shell_command">/s/git reset --hard \([^<]\+\)\s*/git reset --hard %s/' "${seal_rev}"
	sed -i -e "${sed_expr1}" -e "${sed_expr2}" tool_dependencies.xml
	echo "Edited tool_dependencies.xml"

	# edit the tools as well
	printf -v sed_expr3 's|<requirement type="package" version="[^"]\+">seal</requirement>|<requirement type="package" version="%s">seal</requirement>|' "${version_str}"
	sed -i -e "${sed_expr3}" seal/*.xml
	echo "Edited tool definitions"
}

function make_archive() {
	local archive_name=${PackageName}.tar.gz
	tar czf "${archive_name}" seal tool_dependencies.xml tool_data_table_conf.xml.sample README.md
	echo "Created new archive ${archive_name}"
}


function error() {
    if [ $# -ge 1 ]; then
        echo $* >&1
    fi
    exit 1
}

function usage_error() {
    error  "Usage: $0 [ Seal revid ]"
}

if [ $# -gt 2 ]; then
    usage_error
elif [ $# -eq 1 ]; then
    seal_rev="${1}"
else # $# equals 0
    seal_rev=""
fi

if [ -n "${seal_rev}" ]; then
	rewrite_seal_version "${seal_rev}"
fi

make_archive

echo "Don't forget to commit and tag as necessary and then upload the archive to the toolshed!"
