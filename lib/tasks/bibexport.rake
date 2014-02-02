require "rexml/document"

def export_volume_mods volume
	dash = "–"
	papers = volume.papers
	volume_title = volume.title
	year = volume.year
	authors = volume.people
	xml = REXML::Document.new "<?xml version='1.0'?>"
	mods=xml.add_element 'modsCollection'
	title_info = mods.add_element 'titleInfo'
	title_name = title_info.add_element 'title'
	title_name.text = volume_title
	authors.each do |author|
		name = mods.add_element 'name'
		name.attributes["type"]="personal"

		name_part_first = name.add_element 'namePart'
		name_part_first.attributes["type"]="given"
		name_part_first.text = author.first_name

		name_part_last = name.add_element 'namePart'
		name_part_last.attributes["type"]="family"
		name_part_last.text = author.last_name

		role = name.add_element 'role'
		roleterm = role.add_element 'roleTerm'
		roleterm.attributes["authority"]="marcrelator"
		roleterm.attributes["type"]="text"
		roleterm.text="editor"
	end

	origin_info = mods.add_element 'originInfo'
	if volume.publisher
		publisher = origin_info.add_element 'publisher'
		publisher.text = volume.publisher
	end
	if volume.address or volume.url
		volume_location = mods.add_element 'location'
		if volume.address
			volume_address = volume_location.add_element 'physicalLocation'
			volume_address.text = volume.address
		end
		if volume.url
			volume_url = volume_location.add_element 'url'
			volume_url.text = volume.url
		end
	end
	date_issued = origin_info.add_element 'dateIssued'
	date_issued.text = year

	papers.each do |paper|
		if (!((paper.anthology_id[0] == "W" and paper.anthology_id[-2..-1] == "00") or paper.anthology_id[-3..-1] == "000"))
			paper_mods=mods.add_element 'mods'
			paper_mods.attributes["ID"]=paper.anthology_id

			paper_title_info = paper_mods.add_element 'titleInfo'
			paper_title_name = paper_title_info.add_element 'title'
			paper_title_name.text = paper.title
			paper.people.each { |paper_author|
				paper_name = paper_mods.add_element 'name'
				paper_name.attributes["type"]="personal"

				paper_name_part_first = paper_name.add_element 'namePart'
				paper_name_part_first.attributes["type"]="given"
				paper_name_part_first.text = paper_author.first_name

				paper_name_part_last = paper_name.add_element 'namePart'
				paper_name_part_last.attributes["type"]="family"
				paper_name_part_last.text = paper_author.last_name

				paper_role = paper_name.add_element 'role'
				paper_roleterm = paper_role.add_element 'roleTerm'
				paper_roleterm.attributes["authority"]="marcrelator"
				paper_roleterm.attributes["type"]="text"
				paper_roleterm.text="author"
			}
			if (paper.pages)
				part = paper_mods.add_element 'part'
				extent = part.add_element 'extent'
				extent.attributes['unit'] = 'pages'
				startPage = extent.add_element 'start'
				startPage.text = paper.pages.split(dash)[0]
				endPage = extent.add_element 'end'
				endPage.text = paper.pages.split(dash)[1]
			end


			paper_origin_info = paper_mods.add_element 'originInfo'
			if paper.publisher
				paper_publisher = paper_origin_info.add_element 'publisher'
				paper_publisher.text = paper.publisher
			end
			paper_date_issued = paper_origin_info.add_element 'dateIssued'
			paper_date_issued.text = paper.year

			if paper.address or paper.url
				paper_location = paper_mods.add_element 'location'
				if paper.url
					paper_url = paper_location.add_element 'url'
					paper_url.text = paper.url
				end
				if paper.address
					paper_address = paper_location.add_element 'physicalLocation'
					paper_address.text = paper.address
				end
			end


			paper_genre_type = paper_mods.add_element 'genre'
			if( paper.anthology_id[0] == "W")
				paper_genre_type.text = "workshop publication"
			else
				paper_genre_type.text = "conference publication"
			end

			paper_related_item = paper_mods.add_element 'relatedItem'

			paper_related_item.attributes["type"]="host"
			volume_info = paper_related_item.add_element 'titleInfo'
			volume_name = volume_info.add_element 'title'
			volume_name.text = volume.title
		end
	end

	file = File.new("export/mods/#{volume.anthology_id}.xml",'w')
	file.write xml.to_s
	file.close
end

def export_paper_mods paper
	dash = "–"
	paper_title = paper.title
	year = paper.year
	volume_title = paper.volume.title
	authors = paper.people
	id = paper.anthology_id
	url = paper.url
	xml = REXML::Document.new "<?xml version='1.0'?>"
	mods=xml.add_element 'mods'
	mods.attributes["ID"]=id
	title_info = mods.add_element 'titleInfo'
	title_name = title_info.add_element 'title'
	title_name.text = paper_title
	authors.each { |author|
		name = mods.add_element 'name'
		name.attributes["type"]="personal"

		name_part_first = name.add_element 'namePart'
		name_part_first.attributes["type"]="given"
		name_part_first.text = author.first_name

		name_part_last = name.add_element 'namePart'
		name_part_last.attributes["type"]="family"
		name_part_last.text = author.last_name

		role = name.add_element 'role'
		roleterm = role.add_element 'roleTerm'
		roleterm.attributes["authority"]="marcrelator"
		roleterm.attributes["type"]="text"
		roleterm.text="author"

	}
	if (paper.pages)
		part = mods.add_element 'part'
		extent = part.add_element 'extent'
		extent.attributes['unit'] = 'pages'
		startPage = extent.add_element 'start'
		startPage.text = paper.pages.split(dash)[0]
		endPage = extent.add_element 'end'
		endPage.text = paper.pages.split(dash)[1]
	end

	origin_info = mods.add_element 'originInfo'
	date_issued = origin_info.add_element 'dateIssued'
	if paper.publisher
		paper_publisher = origin_info.add_element 'publisher'
		paper_publisher.text = paper.publisher
	end
	date_issued.text = year

	if paper.address or paper.url
		paper_location = mods.add_element 'location'
		if paper.url
			paper_url = paper_location.add_element 'url'
			paper_url.text = url
		end
		if paper.address
			paper_address = paper_location.add_element 'physicalLocation'
			paper_address.text = paper.address
		end
	end

	genre_type = mods.add_element 'genre'
	if( paper.anthology_id[0] == "W")
		genre_type.text = "workshop publication"
	else
		genre_type.text = "conference publication"
	end

	related_item = mods.add_element 'relatedItem'
	related_item.attributes["type"]="host"
	volume_info = related_item.add_element 'titleInfo'
	volume_name = volume_info.add_element 'title'
	volume_name.text = volume_title
	file = File.new("export/mods/#{paper.anthology_id}.xml",'w')
	file.write xml.to_s
	file.close			
end


namespace :export do
	desc "Export paper mods xml"
	task :export_paper_modsxml, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Paper.all.each do |paper|
				puts "exporting paper #{paper.anthology_id}"
				export_paper_mods paper
			end
		else
			export_paper_mods Paper.find_by_anthology_id(args[:anthology_id])
		end
	end

	desc "Export paper bib"
	task :export_paper_bib, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Paper.all.each do |paper|
				puts "converting to bib paper #{paper.anthology_id}"
				`xml2bib export/mods/#{paper.anthology_id}.xml >export/bib/#{paper.anthology_id}.bib`
			end
		else
			paper = Paper.find_by_anthology_id(args[:anthology_id])
			`xml2bib export/mods/#{paper.anthology_id}.xml >export/bib/#{paper.anthology_id}.bib`
		end
	end

	desc "Export paper ris"
	task :export_paper_ris, [:anthology_id]=> :environment do |t, args|
		if not args[:anthology_id]
			Paper.all.each do |paper|
				puts "converting to ris paper #{paper.anthology_id}"
				`xml2ris export/mods/#{paper.anthology_id}.xml >export/ris/#{paper.anthology_id}.ris`
			end
		else
			paper = Paper.find_by_anthology_id(args[:anthology_id])
			`xml2ris export/mods/#{paper.anthology_id}.xml >export/ris/#{paper.anthology_id}.ris`
		end
	end

	desc "Export paper endf"
	task :export_paper_endf, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Paper.all.each do |paper|
				puts "converting to endf paper #{paper.anthology_id}"
				`xml2end export/mods/#{paper.anthology_id}.xml >export/endf/#{paper.anthology_id}.endf`
			end
		else
			paper = Paper.find_by_anthology_id(args[:anthology_id])
			`xml2end export/mods/#{paper.anthology_id}.xml >export/endf/#{paper.anthology_id}.endf`
		end
	end


	desc "Export paper word"
	task :export_paper_word, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Paper.all.each do |paper|
				puts "converting to word paper #{paper.anthology_id}"
				`xml2wordbib export/mods/#{paper.anthology_id}.xml >export/word/#{paper.anthology_id}.word`
			end
		else
			paper = Paper.find_by_anthology_id(args[:anthology_id])
			`xml2wordbib export/mods/#{paper.anthology_id}.xml >export/word/#{paper.anthology_id}.word`
		end
	end


	desc "Export paper dblp"
	task :export_paper_dblp, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Paper.all.each do |paper|
				puts "converting to dblp paper #{paper.anthology_id}"
				`ruby lib/bibscript/mods2dblp.rb export/mods/#{paper.anthology_id}.xml >export/dblp/#{paper.anthology_id}.html`
			end
		else
			paper = Paper.find_by_anthology_id(args[:anthology_id])
			`ruby lib/bibscript/mods2dblp.rb export/mods/#{paper.anthology_id}.xml >export/dblp/#{paper.anthology_id}.html`
		end
	end


	desc "Export volume mods xml"
	task :export_volume_modsxml, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Volume.all.each do |volume|
				puts "exporting volume #{volume.anthology_id}"
				export_volume_mods volume
			end
		else
			export_volume Volume.find_by_anthology_id(args[:anthology_id])
		end
	end

	desc "Export volume bib"
	task :export_volume_bib, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Volume.all.each do |volume|
				puts "converting to bib volume #{volume.anthology_id}"
				`xml2bib export/mods/#{volume.anthology_id}.xml >export/bib/#{volume.anthology_id}.bib`
			end
		else
			volume = Volume.find_by_anthology_id(args[:anthology_id])
			`xml2bib export/mods/#{volume.anthology_id}.xml >export/bib/#{volume.anthology_id}.bib`
		end
	end

	desc "Export volume ris"
	task :export_volume_ris, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Volume.all.each do |volume|
				puts "converting to ris volume #{volume.anthology_id}"
				`xml2ris export/mods/#{volume.anthology_id}.xml >export/ris/#{volume.anthology_id}.ris`
			end
		else
			volume = Volume.find_by_anthology_id(args[:anthology_id])
			`xml2ris export/mods/#{volume.anthology_id}.xml >export/ris/#{volume.anthology_id}.ris`
		end
	end

	desc "Export volume endf"
	task :export_volume_endf, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Volume.all.each do |volume|
				puts "converting to endf volume #{volume.anthology_id}"
				`xml2end export/mods/#{volume.anthology_id}.xml >export/endf/#{volume.anthology_id}.endf`
			end
		else
			volume = Volume.find_by_anthology_id(args[:anthology_id])
			`xml2end export/mods/#{volume.anthology_id}.xml >export/endf/#{volume.anthology_id}.endf`
		end
	end

	desc "Export volume word"
	task :export_volume_word, [:anthology_id]=> :environment do |t, args|
		if not args[:anthology_id]
			Volume.all.each do |volume|
				puts "converting to word volume #{volume.anthology_id}"
				`xml2wordbib export/mods/#{volume.anthology_id}.xml >export/word/#{volume.anthology_id}.word`
			end
		else
			volume = Volume.find_by_anthology_id(args[:anthology_id])
			`xml2wordbib export/mods/#{volume.anthology_id}.xml >export/word/#{volume.anthology_id}.word`
		end
	end

	desc "Export volume dblp"
	task :export_volume_dblp, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Volume.all.each do |volume|
				puts "converting to dblp volume #{volume.anthology_id}"
				`ruby lib/bibscript/mods2dblp.rb export/mods/#{volume.anthology_id}.xml >export/dblp/#{volume.anthology_id}.html`
			end
		else
			volume = Volume.find_by_anthology_id(args[:anthology_id])
			`ruby lib/bibscript/mods2dblp.rb export/mods/#{volume.anthology_id}.xml >export/dblp/#{volume.anthology_id}.html`
		end
	end

	desc "Export volume acm"
	task :export_volume_acm, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Volume.all.each do |volume|
				puts "converting to acm volume #{volume.anthology_id}"
				`ruby lib/bibscript/mods2acm.rb export/mods/#{volume.anthology_id}.xml >export/csv/#{volume.anthology_id}.csv`
			end
		else
			volume = Volume.find_by_anthology_id(args[:anthology_id])
			`ruby lib/bibscript/mods2dblp.rb export/mods/#{volume.anthology_id}.xml >export/dblp/#{volume.anthology_id}.html`
		end
	end
end