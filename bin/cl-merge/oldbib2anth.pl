#!/usr/bin/env perl
#
# Generate an Anthology XML file from BibTeX files
#
# Usage: oldbib2anth.pl input.bib
#
# adapted from bib2anth.pl by Dan Gildea 3/21/2019
# now takes one input bibfile
# finds volume id in bibfile
# creates output files ${volume}.xml
# input must by sorted by volume id, or output files will be overwritten.

use utf8;
use open qw(:std :utf8);

use strict 'vars';

use File::Spec;
use Text::BibTeX;

#my ($dir, $volume_id, $outfile) = @ARGV;
my($bibfilename) = @ARGV;

# check ACLPUB path
die "Need to export ACLPUB=/path/to/acl-pub/assets/files/create_book"
  unless(-d $ENV{ACLPUB});

my $bibfile = Text::BibTeX::File->new($bibfilename);
my $bibentry;
my($volume_id, $last_volume_id);
while ($bibentry = Text::BibTeX::Entry->new({ binmode => 'utf-8', normalization => 'NFC' }, $bibfile)) {
    
    my $url = $bibentry->get('url');
    my $paper_id;
    if ($url =~ m{^http://www.aclweb.org/anthology/([A-Z]\d{2})-(\d{0,4})}) {
	$volume_id = $1;
        $paper_id = $2;
        $paper_id .= "0" while (length($paper_id) < 4);
    } else {
        warn "Aborting: $url in ", $bibentry->key, " is not a valid ACL Anthology URL\n";
	next;
    }

    if ($volume_id ne $last_volume_id) {
	print XML "</volume>\n";
	close XML;
	#open XML, "> $volume_id.xml";
	open XML, "| ./db-to-html.pl -f db > $volume_id.xml";
	print XML '<?xml version="1.0" encoding="UTF-8" ?>',"\n";
	print XML " <volume id=\"$volume_id\">\n";
	# XML to be continued
	$last_volume_id = $volume_id;
    }


    # Convert the current .bib file into XML.

    print XML "   <paper id=\"$paper_id\">\n";

    my %alreadydone;
    for my $field ('title', 'author', 'editor', $bibentry->fieldlist) {   # force order
      next unless $bibentry->exists($field);
      next if $alreadydone{$field}++;

      next if $field eq 'journal';
      next if $field eq 'volume';
      next if $field eq 'number';
      next if $field eq 'annote';
      
      my @values = ($field eq 'author' || $field eq 'editor')
               	       ? map { &formatname($_) } $bibentry->names($field)
		       : &escape_xml($bibentry->get($field));
      for my $val (@values) {
	  if ($field eq 'url') {
	      $val =~ s/.pdf$//;
	  }
	  print XML "        <$field>$val</$field>\n";
      }
    }
    print XML "        <bibtype>".$bibentry->type."</bibtype>\n";
    print XML "        <bibkey>".$bibentry->key."</bibkey>\n";
    print XML "   </paper>\n";
}

print XML " </volume>\n";
close(XML);

###############

# produce name in format <first>Ludwig</first><last>van Beethoven</last>
# bibtex has fields for fist, von, last, and jr
# but anthology database only has fields for first and last.

# We could use Text::BibTeX::NameFormat for this, i.e.,
#     my $format = new Text::BibTeX::NameFormat ('fvlj',0);
#     return $format->apply($name);
# However, customizing that to put XML tags around the pieces is too annoying.

sub formatname {
  my($name) = @_;
  my @tokens = $name->part('first');
  my $out = "<first>".&escape_xml(join(" ",@tokens))."</first>";
  $out .= "<last>";
  @tokens = $name->part('von');
  if (@tokens && $tokens[0]) {   # nonempty
      $out .= &escape_xml(join(" ",@tokens));
      $out .= ' ';
  }
  @tokens = $name->part('last');
  $out .= &escape_xml(join(" ",@tokens));
  @tokens = $name->part('jr');
  if (@tokens && $tokens[0]) {   # nonempty
      # comma before Jr
      $out .= ", " . &escape_xml(join(" ",@tokens));
  }
  $out .= "</last>";    
  if ($out eq lc($out)) {
      # some authors have all lowercase names in their softconf profiles
      # which triggers a bug in TeX::BibTeX name parsing
      # https://github.com/ambs/Text-BibTeX/issues/29
      warn "Lowercase name: $out\n Name may be duplicated/misparsed";
  }
  return $out;
}

sub escape_xml {
    my($text) = @_;
    $text =~ s/&/&amp;/go;
    $text =~ s/</&lt;/go;
    $text =~ s/>/&gt;/go;
#    $text =~ s/'/&apos;/go;
#    $text =~ s/"/&quot;/go;
    return $text;
}
