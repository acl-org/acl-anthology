#!/bin/sh
#
# $1 = version number
# $2 = postfix
# $3 = library target
# $4 = executable extension (.exe for Windows)
#
programs="biblatex2xml bib2xml copac2xml ebi2xml end2xml endx2xml ebi2xml isi2xml med2xml wordbib2xml modsclean ris2xml xml2ads xml2bib xml2end xml2isi xml2ris xml2wordbib"
VERSION=$1
POSTFIX=$2
LIBTARGET=$3
EXEEXT=$4

if [ -e update/bibutils_${VERSION} ] ; then
	rm -r update/bibutils_${VERSION}
fi
mkdir -p update/bibutils_${VERSION}
for p in $programs ; do
	cp bin/${p}${EXEEXT} update/bibutils_${VERSION}/
done
if [ ${LIBTARGET} != libbibutils.a ]; then
	cp lib/${LIBTARGET} update/bibutils_${VERSION}/
fi
cd update
tar cvf - bibutils_${VERSION} | gzip - > bibutils_${VERSION}${POSTFIX}.tgz
cd ..
rm -r update/bibutils_${VERSION}

