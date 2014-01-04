require 'tempfile'
require "rexml/document"

namespace :acl do
	desc "Remove all solr indexes"
	task :export => :environment do
		
		codes = ['A', 'C', 'D', 'E', 'H', 'I', 'J', 'L', 'M', 'N', 'O', 'P', 'Q', 'R' 'S', 'T', 'U', 'W', 'X', 'Y']
		years = ('00'..'13').to_a + ('65'..'99').to_a
		codes.each do |c|
			years.each do |y|
				volume_found = false # by default, the anthology is empty
				xml_doc = REXML::Document.new "<?xml version='1.0'?>"			
				vol = xml_doc.add_element 'volume', {"id" => c + y} # Level 1 indentation
				if c == 'W' # If we have a workshop, the volume series will have 2 digits
					volume_series = (01..99).to_a
				else # else, only count first digit
					volume_series = (1..9).to_a
				end
				volume_series.each do |v|
					@volume = Volume.find_by_anthology_id(c + y + "-" + v.to_s)
					if @volume # Check if volume exists
						volume_found = true
						puts "Exporting volume " + @volume.anthology_id 	
						@papers = @volume.papers
						@papers.each do |paper|
							#puts "Exporting paper " + paper.anthology_id
							pap = vol.add_element 'paper', {"id" => paper.anthology_id[-4..-1]} # Level 2 indentation
							# Level 3 indentation
							title = pap.add_element 'title'
							title.text = paper.title


							
						end
					end
				end # Finished 1 volume

				export_loc = "#{Rails.root}/export/" + c + y + ".xml"
				if volume_found == true
					# Write xml doc to xml file
				    xml_file = File.new("export/" + c + y + ".xml",'w')
				    xml_file.write xml_doc.to_s
				    xml_file.close
				    puts "Saving file " + c + y + ".xml"
				end
			end # finished exporting one anthology, Eg: "E12"
		end 
	end # task export
end