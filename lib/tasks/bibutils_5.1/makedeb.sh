#!/bin/sh
#
# $1 = version number
# $2 = postfix
#
#
# Build up this directory tree/files
#
# update/debian/
#              /DEBIAN/
#                     control
#                     postinst.bibutils
#                     postrm.bibutils
#              /usr/local/bibutils-${1}/
#                                      programs
#
# Then run dpkg on this to build a .deb package
#
programs="biblatex2xml bib2xml copac2xml ebi2xml end2xml endx2xml isi2xml med2xml modsclean ris2xml wordbib2xml xml2ads xml2bib xml2end xml2isi xml2ris xml2wordbib"
VERSION=$1
POSTFIX=$2

if [ "$2" = "_i386" ] ; then
	ARCH="i386"
elif [ "$2" = "_amd64" ] ; then
	ARCH="i386"
elif [ "$2" = "_osx" ] ; then
	ARCH="darwin-powerpc"
else
	echo "Can only accept _i386 _amd64 and _osx as postfixes."
	echo "Skipping make deb for this architecture."
	exit
fi

#
# Clean up any old version
#
if [ -e update/debian ] ; then
	rm -r update/debian
fi
if [ -e update/bibutils-${VERSION}.deb ] ; then
	rm -f update/*.deb
fi
mkdir -p update/debian/DEBIAN
cd update

OUTDIR="debian"
PKGDIR="debian/DEBIAN"

#
# Build control file
#
CNTRL="${PKGDIR}/control"
echo "Package: bibutils"                                                       >  ${CNTRL}
echo "Version:" ${VERSION}                                                     >> ${CNTRL}
echo "Essential: no"                                                           >> ${CNTRL}
echo "Maintainer: Chris Putnam [cdputnam@ucsd.edu]"                            >> ${CNTRL}
echo "Provides: bibutils"                                                      >> ${CNTRL}
echo "Architecture: ${ARCH}"                                                   >> ${CNTRL}
echo "Description: Bibutils converts between bibliography formats"             >> ${CNTRL}
echo "             including BibTeX, RIS, Endnote (Refer), ISI,"               >> ${CNTRL}
echo "             COPAC, and Medline XML using a MODS v3.0 XML intermediate." >> ${CNTRL}

#
# Build post-install script
#
POSTINST="${PKGDIR}/postinst.bibutils"

echo '#!/bin/sh' > ${POSTINST}

#
# Build un-install script
#
POSTRM="${PKGDIR}/postrm.bibutils"

echo '#!/bin/sh' > ${POSTRM}

#
# Build binaries directory
#
# Fink installs on MacOSX install to /sw/bin
#
if [ "${POSTFIX}" = "_i386" ] ; then
	BINARYDIR="${OUTDIR}/usr/local/bin"
elif [ "${POSTFIX}" = "_amd64" ] ; then
	BINARYDIR="${OUTDIR}/usr/local/bin"
elif [ "${POSTFIX}" = "_osx" ] ; then
	BINARYDIR="${OUTDIR}/sw/bin"
fi

mkdir -p ${BINARYDIR}

for program in ${programs} ; do
	cp ../bin/${program} ${BINARYDIR}/.
done

#
# Build update
#
PATH=${PATH}:/sw/bin/:~/src/bibutils/dpkg-1.10.28/main:~/src/bibutils/dpkg-1.10.28/dpkg-deb

dpkg --build ${OUTDIR}  bibutils-${VERSION}${POSTFIX}.deb

rm -r ${OUTDIR}

