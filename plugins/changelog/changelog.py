# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# by Panu Matilainen <pmatilai@laiskiainen.org>
#
# TODO: 
# - In posttrans we could get the changelogs from rpmdb thus avoiding
#   the costly 'otherdata' import but it would be nice to be able to present
#   the changelogs (optionally) *before* the y/n prompt and for that the import
#   would be needed anyway.


import time
from yum.packages import YumInstalledPackage
from rpmUtils.miscutils import splitFilename

requires_api_version = '2.1'

origpkgs = {}
changelog = 0

def changelog_delta(pkg, olddate):
    out = []
    for date, author, message in pkg.returnChangelog():
        if int(date) > olddate:
            out.append("* %s %s\n%s\n" % (time.ctime(int(date)), author, message))
    return out

def srpmname(pkg):
    n,v,r,e,a = splitFilename(pkg.returnSimple('sourcerpm'))
    return n

def config_hook(conduit):
    parser = conduit.getOptParser()
    parser.add_option('--changelog', action='store_true', 
                      help='Show changelog delta of updated packages')

def postreposetup_hook(conduit):
    global changelog
    opts, args = conduit.getCmdLine()
    changelog = opts.changelog

    repos = conduit.getRepos()
    repos.populateSack(with='otherdata')

def pretrans_hook(conduit):
    if not changelog: 
        return

    # Find currently installed versions of packages we're about to update
    ts = conduit.getTsInfo()
    rpmdb = conduit.getRpmDB()
    for tsmem in ts.getMembers():
        for pkgtup in rpmdb.returnTupleByKeyword(name=tsmem.po.name, arch=tsmem.po.arch):
            for hdr in rpmdb.returnHeaderByTuple(pkgtup):
                # store the latest date in changelog entries
                times = hdr['changelogtime']
                n,v,r,e,a = splitFilename(hdr['sourcerpm'])
                origpkgs[n] = times[0]

def posttrans_hook(conduit):
    if not changelog:
        return

    # Group by src.rpm name, not binary to avoid showing duplicate changelogs
    # for subpackages
    srpms = {}
    ts = conduit.getTsInfo()
    for tsmem in ts.getMembers():
        name = srpmname(tsmem.po)
        if srpms.has_key(name):
            srpms[name].append(tsmem.po)
        else:
            srpms[name] = [tsmem.po]

    conduit.info(2, "\nChanges in updated packages:\n")
    for name in srpms.keys():
        rpms = []
        if origpkgs.has_key(name):
            for rpm in srpms[name]:
                rpms.append("%s" % rpm)
            conduit.info(2, ", ".join(rpms))
            for line in changelog_delta(srpms[name][0], origpkgs[name]):
                conduit.info(2, "%s\n" % line)
