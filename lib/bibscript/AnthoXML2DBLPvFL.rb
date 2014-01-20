#!/usr/bin/env ruby
# -*- ruby -*-
# Version 081028
@@BASE_DIR = "/home/antho/"
$:.unshift("#{@@BASE_DIR}/lib/")
require 'rubygems'
require 'optparse'
require 'rexml/document'
require 'time'
include REXML

# defaults
@@VERSION = [1,0]
@@INTERVAL = 100
@@PROG_NAME = File.basename($0)

############################################################
# EXCEPTION HANDLING
int_handler = proc {
  # clean up code goes here
  STDERR.puts "\n# #{@@PROG_NAME} fatal\t\tReceived a 'SIGINT'\n# #{@@PROG_NAME}\t\texiting cleanly"
  exit -1
}
trap "SIGINT", int_handler

############################################################
# PUT CLASS DEFINITION HERE
class AnthoXML2DBLP
  def initialize()
  end

  def process_file(filename)
    infile = File.new(filename)
    in_doc = Document.new infile
    volume_id = in_doc.elements["volume"].attributes["id"]
     
    # prepare output document
    out_doc = Document.new(nil,{:raw=>:all,:respect_whitespace => %w{li}})
    out_doc.add_element(Element.new("html"))
    h = Element.new("header") 
    out_doc.root << h 
    t = Element.new("title")
    h << t 
    b = Element.new("body")
    out_doc.root << b
    h2 = Element.new("h2")
    ul = Element.new("ul")
    b << h2
    b << ul

    # insert volume element
    volume = in_doc.elements["*/paper/title"]
    h2.text = volume.text
    t.text = volume.text
    head_li = Element.new("li")
    ul << head_li
    head_li.text = "X:\nFront Matter.\n"
    head_li.text += "0-"
    head_li << handle_ee(in_doc.elements["*/paper/"],volume_id)
 
    # insert paper elements
    count = 0
    in_doc.elements.each("*/paper/") { |e| 
      count += 1 
      if count == 1 then next end
      li = Element.new("li")
      ul << li
      li.text = ""

      # handle authors
      author_array = Array.new
      had_authors = false
      authors = e.elements.each("author") { |a|
        author_parts = Array.new
        had_authors = true
        a.elements.each { |part|
          author_parts << part.text
        }  
        author_buf = author_parts.join(" ")
        author_array << author_buf
      }
      li.text = author_array.join(",\n")
      if had_authors then li.text += ":\n" end 

      # handle titles
      title = e.elements["title"].text    
      li.text += title 
      if !/[\?\.\!]$/.match(title) then li.text += ". " else li.text += " " end
      li.text += "\n"

      # handle pages
      li.text += handle_pages(e)
    
      li << handle_ee(e, volume_id)
    }
    out_doc.write($stdout)
  end

  def handle_pages(e)
    retval = ""
    pages = e.elements["pages"]
    if pages
      if !/(\d+\D+\d+)/.match(pages.text)
        retval += pages.text + "-" + pages.text
      else 
        retval += pages.text
      end
    else 
      # check if bib file has pages
      if true
	# 
      else 
        retval += "0-"
      end
    end 
    retval += "\n"
    return retval   
  end

  def handle_ee(e, volume)
    # handle electronic editions
    ee = Element.new("ee")
    id = e.attributes["id"]
    ee.text = "http://www.aclweb.org/anthology/#{volume}-#{id}"
    return ee
  end

end

############################################################

# set up options
OptionParser.new do |opts|
  opts.banner = "usage: #{@@PROG_NAME} [options] file_name"

  opts.separator ""
  opts.on_tail("-h", "--help", "Show this message") do STDERR.puts opts; exit end
  opts.on_tail("-v", "--version", "Show version") do STDERR.puts "#{@@PROG_NAME} " + @@VERSION.join('.'); exit end
end.parse!

ax2d = AnthoXML2DBLP.new
ax2d.process_file(ARGV[0])
