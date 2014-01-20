#!/usr/bin/env ruby
# -*- ruby -*-
@@BASE_DIR = "/home/antho/"
$:.unshift("#{@@BASE_DIR}/lib/")
require 'rubygems'
require 'optparse'
require 'ostruct'
require 'rexml/document'
require 'zip/zip'
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
class AnthoXML2AcmCSV
  def compile_filelist(filename)
    infile = File.new(filename)
    in_doc = Document.new infile
    volume_id = in_doc.elements["volume"].attributes["id"]

    # run through paper elements
    filelist = Array.new
    filelist << filename
    in_doc.elements.each("*/paper/") { |e| 
      filelist << File.dirname(filename) + "/" + handle_ee(e,volume_id) + ".pdf"
    }
    return filelist
  end

  def process_file(filename)
    infile = File.new(filename)
    in_doc = Document.new infile
    volume_id = in_doc.elements["volume"].attributes["id"]
 
    # insert volume first line
    retval = "http://www.aclweb.org/anthology/"
    volume_url = File.basename(filename).gsub /\.xml/, ".pdf"
    retval += "#{volume_url}\n"
 
    # insert paper elements
    count = 0
    in_doc.elements.each("*/paper/") { |e| 
      count += 1 
      if count == 1 then next end
#      print "count: #{count} #{e}\n"
      row_elements = Array.new

      # handle pages
      row_elements << handle_pages(e)

      # handle first author last name with tags
      if e.elements["author/last"]
        author_last = e.elements["author/last"].text
      elsif e.elements["author"] # handle just names without markup.  Assume last word is last name
	full_name = e.elements["author"].text
	name_elts = full_name.split
        author_last = name_elts[-1]
      else
        row_elements << "" # no authors
      end
      row_elements << author_last

      # handle electronic edition URL 
      row_elements << "http://www.aclweb.org/anthology/" + handle_ee(e, volume_id)
      retval += row_elements.join(",") + "\n"
    }
    return retval
  end

  def handle_pages(e)
    retval = ""
    pages = e.elements["pages"]
#    print "pages #{pages}\n"
    if pages
      if !match = /((\d+)\D+\d+)/.match(pages.text)
        retval += pages.text 
      else 
        retval += match[2]
      end
    end 
    return retval   
  end

  def handle_ee(e, volume)
    # handle electronic editions
    id = e.attributes["id"]
    return "#{volume}-#{id}"
  end

end

############################################################

# set up options
options = OpenStruct.new
options.zip = false
OptionParser.new do |opts|
  opts.banner = "usage: #{@@PROG_NAME} [options] file_name"

  opts.separator ""
  opts.on_tail("-h", "--help", "Show this message") do STDERR.puts opts; exit end
  opts.on_tail("-v", "--version", "Show version") do STDERR.puts "#{@@PROG_NAME} " + @@VERSION.join('.'); exit end
  opts.on_tail("-z", "--make-zip") do |v| options.zip = v end
end.parse!

ARGV.each do |argv|
  ax2ac = AnthoXML2AcmCSV.new
  if options.zip 
    # make csv file
    rootname = File.basename(argv.gsub(/.xml/,""))
    csv = File.new("/tmp/#{rootname}.csv","w")
    buf = ax2ac.process_file(argv)
    csv.print buf
    print buf
    csv.close

    # compile list of files
    filelist = ax2ac.compile_filelist(argv)
    
    # make zipfile
    Zip::ZipFile.open("#{rootname}.zip", Zip::ZipFile::CREATE) { |zf|
      zf.mkdir(rootname)
      filelist.each do |f|
        if !File.exists?(f) 
          $stderr.puts "# #{@@PROG_NAME} warn\t\tFile \"#{f}\" does not exist!\n" 
        else
          zf.add("#{rootname}/" + File.basename(f),f)
        end
      end
      zf.add("#{rootname}/#{rootname}.csv","/tmp/#{rootname}.csv")
    }

    File.unlink("/tmp/#{rootname}.csv")
  else
    print ax2ac.process_file(argv)
  end
end
