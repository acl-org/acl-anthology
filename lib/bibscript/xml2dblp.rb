require "rexml/document"
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
document = Document.new File.new(fileName)

multiple = XPath.first(document, "//modsCollection")

output = ""

if not multiple
	volume = document.elements["mods/relatedItem/titleInfo/title"].text
	title = document.elements["mods/titleInfo/title"].text
	names = []
	document.elements.each("mods/name") do |element|
		names.push(element.elements["namePart[@type='given']"].text + " " + element.elements["namePart[@type='family']"].text)
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
	volume_title = document.elements["modsCollection/titleInfo/title"].text
	output += "<h2>#{volume_title}</h2>\n"
	listMember = ""

	document.elements.each("modsCollection/mods/") do |mods|
		names = []
		mods.elements.each("name") do |element|
			name = ""
			given = element.elements["namePart[@type='given']"].text
			family = element.elements["namePart[@type='family']"].text
			if given
				name += given + " "
			end
			if family
				name += family
			end
			names.push(name)
		end
		date = mods.elements["originInfo/dateIssued"].text
		paper_title = mods.elements["titleInfo/title"].text
		url = mods.elements["location/url"]
		startPage = mods.elements["part/extent/start"]
		endPage = mods.elements["part/extent/end"]
		listMember += "<li>#{printNames(names)}:\n#{paper_title}.\n"
		if startPage and endPage
			listMember += "#{startPage.text}-#{endPage.text}\n"
		else
			listMember += "0-\n"
		end
		if url
			listMember += "<ee>#{url.text}</ee>\n"
		end
	end
	output += "<ul>#{listMember}</ul>"
end

puts output