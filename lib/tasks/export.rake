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
					volume_series = ('01'..'99').to_a
				else # else, only count first digit
					volume_series = ('1'..'9').to_a
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

							paper.people.each do |person|
								# First we check if the paper is front matter, then we will add editor tags
								if paper.anthology_id[-3..-1] == "000" || (paper.anthology_id[-2..-1] == "00" && c == 'W')
									per = pap.add_element 'editor'
								else # If it is not, we add author tags 
									per = pap.add_element 'author'
								end
								first_name	= per.add_element 'first'
								last_name	= per.add_element 'last'
								first_name.text = person.first_name
								last_name.text 	= person.last_name
							end
							
							# Volumes do not have booktitles
							if not(paper.anthology_id[-3..-1] == "000" || (paper.anthology_id[-2..-1] == "00" && c == 'W'))
								booktitle = pap.add_element 'booktitle'
								booktitle.text = @volume.title
							end
							if paper.month
								month = pap.add_element 'month'
								month.text = paper.month
							end
							if paper.year
								year = pap.add_element 'year'
								year.text = paper.year
							end
							if paper.address
								address = pap.add_element 'address'
								address.text = paper.address
							end
							if paper.publisher
								publisher = pap.add_element 'publisher'
								publisher.text = paper.publisher
							end
							if paper.pages
								pages = pap.add_element 'pages'
								pages.text = paper.pages
							end
							if paper.url
								url = pap.add_element 'url'
								url.text = paper.url
							end
							if paper.bibtype
								bibtype = pap.add_element 'bibtype'
								bibtype.text = paper.bibtype
							end
							if paper.bibkey
								bibkey = pap.add_element 'bibkey'
								bibkey.text = paper.bibkey
							end
							if paper.attachment != "none"
								if paper.attach_type == "attachment"
									attachment = pap.add_element 'attachment'
									attachment.text = paper.attachment
								elsif paper.attach_type == "dataset"
									attachment = pap.add_element 'dataset'
									attachment.text = paper.attachment
								elsif paper.attach_type == "software"
									attachment = pap.add_element 'software'
									attachment.text = paper.attachment
								end
							end
						end # Finished all papers in the volume
					end
				end # Finished all volumes

				export_loc = "#{Rails.root}/export/" + c + y + ".xml"
				if volume_found == true
					# Write xml doc to xml file
					xml_file = File.new("export/" + c + y + ".xml",'w')
					xml_string = xml_doc.to_s
					xml_string.gsub!(/amp;/, '') # delete all escape chars, &amp; => &
					xml_string.force_encoding('UTF-8').encode('UTF-8', :invalid => :replace, :undef => :replace, :replace => '')
	
					xml_file.write xml_string
					xml_file.close
					puts "Saving file " + c + y + ".xml"
				end
			end # finished exporting one anthology, Eg: "E12"
		end 
	end # task export
end