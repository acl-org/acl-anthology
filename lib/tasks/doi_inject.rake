# encoding: UTF-8
require "rexml/document"

DOI_PREFIX="10.3115/v1"

def get_doi_from_url(url)
    start = url.rindex("/") + 1
    anthology_id = url[start..-1]
    return DOI_PREFIX + "/" + anthology_id
end

def process_volume_xml(volume_num, xml_data, excluded_workshops)
    xml_data.force_encoding('UTF-8').encode('UTF-8', :invalid => :replace, :undef => :replace, :replace => '')
	xml_data = HTMLEntities.new.decode xml_data # Change all escape characters to Unicode
	xml_data.gsub!(/&/, '&amp;') 
	xml_data.gsub!(/<</, '&lt;&lt;') 
	xml_data.gsub!(/>>/, '&gt;&gt;')
	xml_data.gsub!(/--/, '-') 

    xml_doc = REXML::Document.new xml_data
	xml_doc.elements.each("volume/paper") do |paper|
	    id = format('%02d', paper.attributes["id"].to_i/100)
	    anthology_id = volume_num + "-" + id

        publisher = ""
        if !excluded_workshops.include?(anthology_id)
            if !paper.elements["publisher"].nil?
    	        publisher = paper.elements["publisher"].text 
    	    end
    
    	    # ACL paper only
            if publisher.include?("Association for Computational Linguistics")
        	    url = paper.elements["url"]
        	    if url and paper.elements["doi"].nil?
        	        doi = REXML::Element.new("doi")
        	        doi.text = get_doi_from_url(url.text)
        	        paper.insert_after(url, doi)
        	    end
            end
        end
    end
	return xml_doc
end

=begin
Inject the DOI into import/.xml for papers published by ACL after 2012.
P: ACL, D: EMNLP, E: EACL, N: NAACL, S: SemEval/Sem, W: Workshops by ACL, Q: TACL

Note: 
1. The presence of DOIs will be checked, and thus papers with DOIs will be skipped.
2. Papers from non-ACL publishers will be automatically skipped.
3. Papers from workshops specified in the parameter will be skipped.

Usage:
    Please specify the proceeding and the workshops that should be skipped in the
    parameter. Multiple workshops are seperated by a whitespace.
    
    E.g.,
    rake import:doi[W15,'W15-01 W15-02 W15-03 W15-04 W15-18 W15-19 W15-20 W15-21']
    or rake import:doi[P15] 
=end	
namespace :import do
    desc "Inject doi to import/xml files"
    task :doi, [:proceeding, :excluded] => :environment do |t, args|
        volume = args.proceeding
        if !args.excluded.nil?
            excluded_workshops = args.excluded.strip.split.to_set
        else
            excluded_workshops = Set.new
        end
        file_path = "import/" + volume + ".xml"
        if File.exist?(file_path)
            puts "Processing " + file_path
            String xml_data = File.read(file_path)
            xml_doc = process_volume_xml(volume, xml_data, excluded_workshops)
            
            xml_file = File.new(file_path, "w:UTF-8")
            formatter = REXML::Formatters::Pretty.new(2)
        	formatter.compact = true # pretty-printing
    		xml_string = ""
    		formatter.write(xml_doc, xml_string)
    		xml_string.gsub!(/amp;/, '') # delete all escape chars, &amp; => &
    		xml_string.force_encoding('UTF-8').encode('UTF-8', :invalid => :replace, :undef => :replace, :replace => '')
    
    		xml_file.write xml_string
    		xml_file.close
        else
    	    puts file_path + " does not exist!"
        end
    end # Finished task
end