# encoding: UTF-8
require "rexml/document"

DOI_PREFIX="10.3115/v1"

def get_doi_from_url(url)
    start = url.rindex("/") + 1
    anthology_id = url[start..-1]
    return DOI_PREFIX + "/" + anthology_id
end


# Some workshops should be excluded, although their publishers are ACL. 
def is_excluded_workshop(anthology_id)
	return anthology_id=='W15-01' || anthology_id=='W15-02' ||
		   anthology_id=='W15-03' || anthology_id=='W15-04' ||
		   anthology_id=='W15-18' || anthology_id=='W15-19' ||
		   anthology_id=='W15-20' || anthology_id=='W15-21' 
end


def process_volume_xml(volume_num, xml_data)
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
        if !is_excluded_workshop(anthology_id)
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
1. The presence of DOIs will be checked, and papers with DOIs are skipped.
2. Papers from non-ACL publishers will be automatically skipped.
3. Papers from specified workshops (see the list in is_excluded_workshop method) 
   will be skipped, although their publisher is ACL.

Usage:
    Please specify the proceeding to be injected in the parameter. E.g.,
    rake inject:doi_inject[P15] 
    
=end	
namespace :inject do
    desc "Inject doi to import/xml files"
    task :doi_inject, [:proceeding] => :environment do |t, args|
        volume = args.proceeding
        file_path = "import/" + volume + ".xml"
        if File.exist?(file_path)
            puts "Processing " + file_path
            String xml_data = File.read(file_path)
            xml_doc = process_volume_xml(volume, xml_data)
            
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