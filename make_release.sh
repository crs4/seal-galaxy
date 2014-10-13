#!/bin/bash

#set -x
set -o errexit
set -o nounset
set -o pipefail

PackageName="seal-galaxy"


function error() {
    if [ $# -ge 1 ]; then
        echo $* >&1
    fi
    exit 1
}

function usage_error() {
    echo "Usage: $0 version"
    echo "Specify version as a git revid (id or tag) for the Seal repository, and " >&2
    echo "optionally a '-n' suffix for the wrapper version; e.g., 0.4.1, 0.4.1-1, 0.4.1-2" >&2
    error
}

function confirm() {
    local prompt="${1}"
    echo "${prompt} [Y/n]"
    read -p "Answer: " yn
    case "${yn}" in
        ''|[Yy]) # do nothing and keep going
            ;;
        [Nn]) echo "Aborting"; exit 0
            ;;
        *) usage_error "Unrecognized answer. Please specify Y or n"
            ;;
    esac
    return 0
}

function rewrite_seal_version() {
	local grep_expr='<package name="seal" version=".*">'
	if ! grep  "${grep_expr}" tool_dependencies.xml >/dev/null ; then
			error "Couldn't find expected package line in tool_dependencies.xml"
	fi

	printf -v sed_expr1  '/<package name="seal"/s/version="[^"]*"/version="%s"/' "${seal_version}"
	printf -v sed_expr2  '/<action type="shell_command">/s/git reset --hard \([^<]\+\)\s*/git reset --hard %s/' "${seal_version}"
	sed -i -e "${sed_expr1}" -e "${sed_expr2}" tool_dependencies.xml
	echo "Edited tool_dependencies.xml" >&2

	# edit the tools as well
	printf -v sed_expr3 '/<requirement type="package" version=.*>\s*seal\s*</s/version="[^"]\+"/version="%s"/' "${seal_version}"
	printf -v sed_expr4 '/<tool id=/s/version="[^"]\+"/version="%s"/' "${seal_version}"
	sed -i -e "${sed_expr3}" -e "${sed_expr4}" seal/*.xml

	echo "Edited tool definitions" >&2
}

############# main ###############3

if [ $# -eq 1 ]; then
    wrapper_version="${1}"
else
    usage_error
fi

echo "Will rewrite tool_dependencies.xml setting the the package version to '${wrapper_version}'."
confirm "Are you sure you want to proceed? [Y/n]"

# ensure the tag doesn't already exist
if git tag -l | grep -w "${wrapper_version}" ; then
    error "A release tag called '${wrapper_version}' already exists"
fi

# remove the wrapper suffix, if it's there
seal_version=$(echo ${wrapper_version} | sed -e 's/-[^-]\+$//')
echo "Using seal version ${seal_version}"

rewrite_seal_version "${seal_version}"

git commit -a -m "Wrappers release for Seal '${seal_version}'"
git tag "${wrapper_version}"

revid=$(git rev-parse HEAD)

echo "Tagged new commit ${revid} with tag '${wrapper_version}'"

short_revid=${revid::8}
archive_name=${PackageName}-${short_revid}.tar.gz

git archive --format tar.gz --prefix ${PackageName}-${short_revid}/ HEAD -o "${archive_name}"

echo "Don't forget to upload the archive to the toolshed!"
