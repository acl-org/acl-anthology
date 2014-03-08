require "rexml/document"
require 'htmlentities'

include REXML

def printNames(names)
	result = ""
	for i in 0..names.size-1 do
		result += names[i]
		if i != (names.size() -1)
			result += ", "
		end
	end
	result
end

fileName = ARGV[0]
xml_data = File.read(fileName)
xml_data.gsub!(/&/, '&amp;')

document = Document.new xml_data

multiple = XPath.first(document, "//modsCollection")

output = ""

if not multiple
	volume = document.elements["mods/relatedItem/titleInfo/title"].text
	title = document.elements["mods/titleInfo/title"].text
	names = []
	document.elements.each("mods/name") do |element|
		names.push(element.elements["namePart[@type='given']"].text|| "" + " " + element.elements["namePart[@type='family']"].text || "")
	end

	date = document.elements["mods/originInfo/dateIssued"].text
	url = document.elements["mods/location/url"]
	startPage = document.elements["part/extent/start"]
	endPage = document.elements["part/extent/end"]

	output += "<h2>#{volume}, #{date}</h2>\n"
	output += "<ul>\n<li>#{printNames(names)}:\n#{title}.\n"
	if startPage and endPage
		output += "#{startPage.text}-#{endPage.text}\n"
	else
		output += "0-\n"
	end
	if url
		output+= "<ee>#{url.text}</ee>\n"
	end
	output += "</ul>"
else
	xml_doc = REXML::Document.new 
	puts "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>"
	puts "<!DOCTYPE dblpsubmission SYSTEM \"dblpsubmission.dtd\">"
	puts "<?xml-stylesheet type=\"text/xsl\" href=\"dblpsubmission.xsl\" ?>\n"
	#dt = DocType.new('dblpsubmission SYSTEM', "dblpsubmission.dtd")
	#xml_doc.add_element dt
	dblp = xml_doc.add_element 'dblpsubmission'
	vol = dblp.add_element 'proceedings'
		
	vol_tag = document.elements["modsCollection"]

	vol_tag.elements.each("name") do |editor_tag|
		editor = ""
		given = editor_tag.elements["namePart[@type='given']"].text if editor_tag.elements["namePart[@type='given']"]
		family = editor_tag.elements["namePart[@type='family']"].text if editor_tag.elements["namePart[@type='family']"]
		if given
			editor += given + " "
		end
		if family
			editor += family
		end
		if editor.length
			ed = vol.add_element 'editor'
			ed.text = editor
		end
	end
	
	title = vol.add_element 'title'
	title.text = vol_tag.elements["titleInfo/title"].text if vol_tag.elements["titleInfo/title"]

	pub = vol.add_element 'publisher'
	pub.text = vol_tag.elements["originInfo/publisher"].text if vol_tag.elements["originInfo/publisher"]
	year = vol.add_element 'year'
	year.text = vol_tag.elements["originInfo/dateIssued"].text if vol_tag.elements["originInfo/dateIssued"]

	conf = vol.add_element 'conf'
	loc = conf.add_element 'location'
	loc.text = vol_tag.elements["location/physicalLocation"].text if vol_tag.elements["location/physicalLocation"]
	date = conf.add_element 'date'
	date.text = vol_tag.elements["originInfo/dateIssued"].text if vol_tag.elements["originInfo/dateIssued"]
	url = conf.add_element 'url'
	url.text = vol_tag.elements["location/url"].text if vol_tag.elements["location/url"]

	toc = vol.add_element 'toc'
	vol_tag.elements.each("mods/") do |mods|
		publ = toc.add_element 'publ'
		mods.elements.each("name") do |author_tag|
			author = ""
			given = author_tag.elements["namePart[@type='given']"].text if author_tag.elements["namePart[@type='given']"]
			family = author_tag.elements["namePart[@type='family']"].text if author_tag.elements["namePart[@type='family']"]
			if given
				author += given + " "
			end
			if family
				author += family
			end
			if author.length
				au = publ.add_element 'author'
				au.text = author
			end
		end

		ti = publ.add_element 'title'
		ti.text = mods.elements["titleInfo/title"].text

		if mods.elements["part/extent/start"] && mods.elements["part/extent/end"] && mods.elements["part/extent/start"].text && mods.elements["part/extent/end"].text
			pages = publ.add_element 'pages'
			pages.text = mods.elements["part/extent/start"].text + "-" + mods.elements["part/extent/end"].text
		end
	end


	output = xml_doc.to_s

	# listMember = ""

	# document.elements.each("modsCollection/mods/") do |mods|
	# 	
	# 	date = mods.elements["originInfo/dateIssued"].text
	# 	paper_title = mods.elements["titleInfo/title"].text
	# 	url = mods.elements["location/url"]
	# 	startPage = mods.elements["part/extent/start"]
	# 	endPage = mods.elements["part/extent/end"]
	# 	listMember += "<li>#{printNames(names)}:\n#{paper_title}.\n"
	# 	if startPage and endPage
	# 		listMember += "#{startPage.text}-#{endPage.text}\n"
	# 	else
	# 		listMember += "0-\n"
	# 	end
	# 	if url
	# 		listMember += "<ee>#{url.text}</ee>\n"
	# 	end
	# end
	# output += "<ul>#{listMember}</ul>"
end

puts output