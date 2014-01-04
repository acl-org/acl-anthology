require 'tempfile'
require "rexml/document"

namespace :acl do
	desc "Remove all solr indexes"
	task :export => :environment do
		
		codes = ['A', 'C', 'D', 'E', 'H', 'I', 'J', 'L', 'M', 'N', 'O', 'P', 'Q', 'R' 'S', 'T', 'U', 'W', 'X', 'Y']
		years = ('00'..'13').to_a + ('65'..'99').to_a
		codes.each do |c|
			years.each do |y|
				xml_file = REXML::Document.new "<?xml version='1.0'?>"
				export_loc = "#{Rails.root}/export/" + c + y + ".xml"
				vol = xml_file.add_element 'volume', {"id" => c + y}
				if c == 'W' # If we have a workshop, the volume series will have 2 digits
					volume_series = (01..99).to_a
				else # else, only count first digit
					volume_series = (1..9).to_a
				end
				volume_series.each do |v|
					@volume = Volume.find_by_anthology_id(c + y + "-" + v.to_s)
					if @volume # Check if volume exists
						puts "Exporting volume " + @volume.anthology_id 	
						@papers = @volume.papers
						@papers.each do |paper|
							#puts "Exporting paper " + paper.anthology_id
							


							
						end
					end
				end # Finished 1 volume
			end # finished exporting one anthology, Eg: "E12"
		end 
	end # task export
end