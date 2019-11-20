#! /usr/bin/env perl
# -*- coding: utf-8 -*-
#
# Copyright 2018 Min-Yen Kan  <kanmy@comp.nus.edu.sg>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

use File::Glob ':bsd_glob';

sub FileToString {
    local ($fn, *str) = @_;
    if (-e $fn) {
	open(IN, "<$fn");
	binmode(IN);
	my @fl = <IN>;
	$str = join("", @fl);
	close IN;
    }
    else {
	$str = "";
    }
}

sub StringToNewFile {
    local ($str, $fn) = @_;
    open (FILE, ">$fn");
    binmode(FILE);
    print FILE $str;
    flush FILE;
    close FILE;
}

@thefilelist = bsd_glob("*.xml");

foreach $fn (@thefilelist) {
  my $thefile = '';
  FileToString($fn, \$thecontent);

  # reference: https://en.wikipedia.org/wiki/List_of_XML_and_HTML_character_entity_references
  $thecontent =~ s/&rsquo;/&#x2019;/g;
  $thecontent =~ s/&lsquo;/&#x2018;/g;
  $thecontent =~ s/&rdquo;/&#x201D;/g;
  $thecontent =~ s/&ldquo;/&#x201C;/g;
  $thecontent =~ s/&agrave;/&#x00E0;/g;
  $thecontent =~ s/&aacute;/&#x00E1;/g;
  $thecontent =~ s/&Aacute;/&#x00C1;/g;
  $thecontent =~ s/&ccedil;/&#x00E7;/g;
  $thecontent =~ s/&Ccedil;/&#x00C7;/g;
  $thecontent =~ s/&egrave;/&#x00E8;/g;
  $thecontent =~ s/&eacute;/&#x00E9;/g;
  $thecontent =~ s/&oacute;/&#x00F3;/g;
  $thecontent =~ s/&uuml;/&#x00FC;/g;
  $thecontent =~ s/&ouml;/&#x00F6;/g;
  $thecontent =~ s/&auml;/&#x00E4;/g;
  $thecontent =~ s/&euml;/&#x00EB;/g;
  $thecontent =~ s/&iuml;/&#x00EF;/g;
  $thecontent =~ s/&iacute;/&#x00ED;/g;
  $thecontent =~ s/&ntilde;/&#x00F1;/g;
  $thecontent =~ s/&Eacute;/&#x00C9;/g;
  $thecontent =~ s/&atilde;/&#x00E3;/g;
  $thecontent =~ s/&Ouml;/&#x00D6;/g;
  $thecontent =~ s/&uacute;/&#x00FA;/g;
  $thecontent =~ s/&Oslash;/&#x00D8;/g;
  $thecontent =~ s/&oslash;/&#x00F8;/g;
  $thecontent =~ s/&aring;/&#x00E5;/g;
  $thecontent =~ s/&ecirc;/&#x00EA;/g;
  $thecontent =~ s/ & / &amp; /g;
  # $thecontent =~ s/&;/&#x/g;
  # $thecontent =~ s/&;/&#x/g;
  # $thecontent =~ s/&;/&#x/g;
  # $thecontent =~ s/&;/&#x/g;
  # $thecontent =~ s/&;/&#x/g;
  # $thecontent =~ s/&;/&#x/g;
  # $thecontent =~ s/&;/&#x/g;
  # $thecontent =~ s/&;/&#x/g;
  # $thecontent =~ s/&;/&#x/g;
  # $thecontent =~ s/&;/&#x/g;
  # $thecontent =~ s/&;/&#x/g;
  # $thecontent =~ s/&;/&#x/g;
  # $thecontent =~ s/&;/&#x/g;
  StringToNewFile($thecontent, $fn);
}
