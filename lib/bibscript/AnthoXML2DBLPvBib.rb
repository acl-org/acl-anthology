#!/usr/bin/env ruby
# -*- ruby -*-
require "rexml/document"
require "rexml/xpath"
require 'optparse'
require 'ostruct'
require 'time'

# defaults
@@VERSION = [1,0]
@@INTERVAL = 100
@@PROG_NAME = File.basename($0)
@@DEBUG = false
@@OPT_X = false
############################################################
# EXCEPTION HANDLING
int_handler = proc {
  # clean up code goes here
  STDERR.puts "\n# #{@@PROG_NAME} fatal\t\tReceived a 'SIGINT'\n# #{@@PROG_NAME}\t\texiting cleanly"
  exit -1
}
trap "SIGINT", int_handler

def canonicalize(str) 
  str.sub!(/\s+$/,"")
  str.sub!(/^\s+/,"")
  str
end

def process_volume(p, prefix, in_volume)
  pid = p.attributes["id"]
  buf = ""
  if (in_volume == true) 
    buf += "</ul>\n"
  end

  buf += "<h2>" + canonicalize(p.elements["title"].text) + "</h2>\n"

  buf += "<ul>\n"
  buf += "<li>X:\nFront Matter.\n0-\n"
  buf += "<ee>#{prefix}#{pid}</ee>\n"
  buf 
end

def process_paper(p, prefix, path, stem)
  # init
  authors = ""
  page_range = "0-"
  pid = p.attributes["id"]
  href = p.attributes["href"]
  ee = ""

  # authors
  authors = Array.new
  p.elements.each("author") { |a|
    #if (a.elements["first"].text != nil)
    if (a.elements["first"] != nil) # Thang fix
      author = canonicalize(a.elements["first"].text) + " " + canonicalize(a.elements["last"].text)
    else
      author = a.text
      begin
        if (author.match(/,/))
          STDERR.puts "comma detected in author name for paper ##{pid}\t#{author}"
        end
      rescue
        # no author
      end
    end
    
    if (author == nil) 
      STDERR.puts "No author correctly found for paper ##{pid}, dying!"
      exit(-1)
    end
    authors.push(canonicalize(author))
  }
  authorString = authors.join(", ") + ":"

  # title
  title = canonicalize(p.elements["title"].text)
  if title.match(/[a-z0-9A-Z]$/)
    title += "."
  end

  # ee (points now to anthology, use -x to extract DOI from bib file)
  ee = prefix + pid

  # page range (from <pages> in XML, else from bib file if present)
  doi = ""
  pages = p.elements["pages"]
  if (pages != nil)
    page_range = pages.text
  else 
    bib_file = "#{path}#{stem}-#{pid}.bib"
    pages = ""
    begin
      bf = File.open(bib_file) 
      bf.each { |l|
        if (md = l.match(/^\s*doi\s*=\s*\{(.+)\}\s*/)) then doi = md[1] end
        if (md = l.match(/^\s*pages\s*=\s*\{(.+)\}\s*/)) then pages = md[1] end

        if (pages = l.match(/\-/))
          page_range = pages.sub(/\-/,"")
        else
          page_range = pages.sub(/&#8211;/,"")
        end
        ee = doi if @@OPT_X
     }
     bf.close
    rescue
      STDERR.puts "Warning no bib file for #{pid}."
    end
  end

  if (@@DEBUG) then puts "BIBFILE #{bib_file}" end
  if (href != nil)
    buf = "<li>#{authorString}\n#{title}\n#{page_range}\n<ee>#{href}</ee>\n"
  else
    buf = "<li>#{authorString}\n#{title}\n#{page_range}\n<ee>#{ee}</ee>\n"
  end
end

############################################################
# set up options
# @@options = OpenStruct.new
@@MODE = "conference"
OptionParser.new do |opts|
  opts.banner = "usage: #{@@PROG_NAME} [options] antho_file.xml > dblp_file.html"

  opts.separator ""
  opts.on_tail("-d", "--debug", "Turn record matching debugging on") do @@DEBUG = true end
  opts.on_tail("-m", "--mode [MODE]", "operation mode (either workshop or default: conference)") do |opt|
    @@MODE = opt || nil
  end
  opts.on_tail("-h", "--help", "Show this message") do puts opts; exit end
  opts.on_tail("-v", "--version", "Show version") do puts "#{@@PROG_NAME} " + @@VERSION.join('.'); exit end
  opts.on_tail("-x", "--extract_doi", "Electronic edition to DOI instead of ACL Anthology") do @@OPT_X = true end
end.parse!

############################################################
# Main program
f = File.open(ARGV[0])
basename = ""
path = ""
if (md = ARGV[0].match(/(.+\/)([^\/]+$)/))
  basename = md[-1]
  path = md[1]
else
  basename = ARGV[0]
  path = ""
end
case @@MODE
when "workshop"
  stem = basename.split(/\./)[0..-2].join
  stem = stem.split(/\-/)[0..-2].join 
  volumePattern = "00";
when "conference"
  stem = basename.split(/\./)[0..-2].join
  volumePattern = "000";
end

prefix = "http://www.aclweb.org/anthology/#{stem}-"

doc = REXML::Document.new f

in_volume = false
doc.elements.each("//paper") { |p|
  if (p.attributes["id"].match(/#{volumePattern}$/)) #Thang modify replace 000 by #{volumePattern}
    buf = process_volume(p,prefix,in_volume)
  else 
    buf = process_paper(p,prefix,path,stem)
    in_volume = true
  end
  puts buf
}
puts "</ul>"
