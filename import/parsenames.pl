#!/bin/perl -i.bak

# usage:
# parsenames.pl *xml 

# processes files in place and and leaves .bak files

# looks for
# <author>...</author>
# <editor>...</editor>
# and adds tags for <first> and <last>

use Text::BibTeX::Name;

while (<>) {
    s/<(author|editor)>\s*(\S[^<]*)\s*<\/(author|editor)>/ {
	my $name = Text::BibTeX::Name->new($2);
	$out = &formatname($name);
        "<$1>$out<\/$1>" } /e;
    print;
}

# takes Text::BibTeX::Name object
# prints name in format <first>Ludwig</first><last>van Beethoven</last>        
# bibtex has fields for fist, von, last, and jr                                 
# but anthology database only has fields for first and last.                    
sub formatname {
  my($name) = @_;
  my @tokens = $name->part('first');
  my $out = "<first>".join(" ",@tokens)."</first>";
  $out .= "<last>";
  @tokens = $name->part('von');
  if (@tokens && $tokens[0]) {   # nonempty
      $out .= join(" ",@tokens);
      $out .= ' ';
  }
  @tokens = $name->part('last');
  $out .= join(" ",@tokens);
  @tokens = $name->part('jr');
  if (@tokens && $tokens[0]) {   # nonempty
      # comma before Jr
      $out .= ", " . join(" ",@tokens);
  }
  $out .= "</last>";
  return $out;
}
