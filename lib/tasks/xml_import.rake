require "rexml/document"
require "net/http"
require "uri"
require 'htmlentities'

def parse_name(full_name)
  if full_name.split(',') == 2 # If the format is Last Name, First
    first_name = full_name.split(',')[1]
    last_name = full_name.split(',')[0]
  else # Splits "This Is Name" into "This Is" and "Name"
    first_name = full_name.split[0..-2].join(" ")
    last_name = full_name.split[-1]
  end
  return first_name, last_name
end

def load_volume_xml(xml_data)
  
  xml_data.force_encoding('UTF-8').encode('UTF-8', :invalid => :replace, :undef => :replace, :replace => '')
  xml_data.gsub!(/&amp;/, '&amp;amp;')	# three chars that need to stay
  xml_data.gsub!(/&gt;/, '&amp;gt;')	#  escaped in xml
  xml_data.gsub!(/&lt;/, '&amp;lt;')	# will go back to &amp; &gt; &lt;

  xml_data = HTMLEntities.new.decode xml_data # Change all escape characters to Unicode
  # handles html entities such as &eacute; that are not known in xml

  xml_data.gsub!(/<</, '&lt;&lt;') 
  xml_data.gsub!(/>>/, '&gt;&gt;')
  xml_data.gsub!(/--/, '-') 
  
  doc = REXML::Document.new xml_data
  doc = doc.elements[1] # skipping the highest level tag
  
  id = doc.attributes["id"] # The document id in the first "volume" tag, eg. E12
  @curr_volume = Volume.new # Stores the current volume so the papers are saved to it
  
  # We will check if the xml is of a type workshop. If it is, each workshop ending with 00 will be treated as 1 volume
  w_check = "000" # default check for volumes
  w_num = -3 # default number of last chars checked (stands for 3)
  if id[0] == 'W'
    w_check = "00"
    w_num = -2
  end

  counter = 0  
  (1..doc.size/2).each do |i| # Loop trough all the paper tags in the doc, has to be /2 because each tag is counted twice
    if doc.elements[i].attributes["id"][w_num..-1] == w_check 
      vol = doc.elements[i] # Short hand for easier reading
      
      @volume = Volume.new
      if id[0] == 'W' # If the volume is a workshop, then use the first 2 digits of the ID
        @volume.anthology_id = id + '-' + vol.attributes["id"][0..1] # W12-01
      else # If not, only use the first digit
        @volume.anthology_id = id + '-' + vol.attributes["id"][0] # D13-1
      end
      @volume.title = vol.elements['title'].text if vol.elements['title']
      @volume.journal_name = vol.elements['journal_name'].text if vol.elements['journal_name']
      
      @front_matter = Paper.new
      @front_matter.anthology_id = id + '-' + vol.attributes["id"]

      if counter % 10 == 0
        print "[#{@front_matter.anthology_id}]"
      end
      @front_matter.title = @volume.title
      
      # Adding editor information
      vol.elements.each('editor') do |editor|
        first_name = ""
        last_name = ""
        full_name = ""
        if editor.elements['first'] || editor.elements['last'] # Check if there are first,last name tags 
          first_name = editor.elements['first'].text	if editor.elements['first']
          last_name = editor.elements['last'].text	if editor.elements['last']
          first_name = "" if first_name == nil
          last_name = "" if last_name == nil
          full_name = first_name + " " + last_name
        else # If not, manually split the name into first name, last name
          full_name = editor.text
          first_name, last_name = parse_name(full_name)
        end
        @editor = Person.find_or_create_by_first_name_and_last_name_and_full_name(first_name, last_name, full_name)
        @volume.people << @editor # Save join person(editor) - volume to database
        @front_matter.people << @editor
      end
      
      @volume.month 		= vol.elements['month'].text		if vol.elements['month']
      if vol.elements['year']
        @volume.year 	= (vol.elements['year'].text).to_i
      else
        @volume.year 	= ("20" + id[1..2]).to_i if id[1..2].to_i < 20
        @volume.year 	= ("19" + id[1..2]).to_i if id[1..2].to_i > 60
      end
      @volume.address 	= vol.elements['address'].text		if vol.elements['address']
      @volume.publisher 	= vol.elements['publisher'].text	if vol.elements['publisher']
      @volume.url 		= "http://aclweb.org/anthology/" + @volume.anthology_id
      @volume.bibtype 	= vol.elements['bibtype'].text		if vol.elements['bibtype']
      @volume.bibkey 		= vol.elements['bibkey'].text		if vol.elements['bibkey']
      
      # volume numbers for journal articles
      if (vol.elements["volume"])
        # <volume> tag in xml file takes precedence
        @volume.journal_volume = vol.elements["volume"].text
      elsif @volume.anthology_id[0] == 'J' && @volume.year > 1979
        # if <volume> tag not found, convert year to volume number for CL
        @volume.journal_volume = ( @volume.year - 1974 ).to_s
        # replace "Computational Linguistics, Volume 18, Issue 1"
        # with    "Computational Linguistics"
        @volume.journal_name = @volume.title.sub(/[-–, ]*Volume .*/, '')
      elsif @volume.anthology_id[0] == 'Q'
        # convert year to volume number for TACL
        @volume.journal_volume = ( @volume.year - 2012 ).to_s
        @volume.journal_name = @volume.title.sub(/[-–, ]*Volume .*/, '')
      end

      # issue numbers for journal articles
      if (vol.elements["issue"])
        # <issue> tag in xml file takes precedence
        @volume.journal_issue = vol.elements["issue"].text
      elsif @volume.anthology_id[0] == 'J'
        # otherwise, the thousands place in the paper id is the issue number for CL
        @volume.journal_issue = ( vol.attributes["id"].to_i / 1000 ).to_s
        # TACL has no issue number
      end

      @volume.save # Save volume
      @curr_volume = @volume
      
      @front_matter.month		= @volume.month
      @front_matter.year		= @volume.year
      @front_matter.address	= @volume.address
      @front_matter.publisher	= @volume.publisher
      @front_matter.url		= "http://aclweb.org/anthology/" + @front_matter.anthology_id
      @front_matter.bibtype	= @volume.bibtype
      @front_matter.bibkey	= @volume.bibkey
      
      if @front_matter.anthology_id[0] != 'J' # Journals don't have front matter
        @curr_volume.papers << @front_matter # Save front_matter
      end
      
    else # If not, we assume it is a paper
      p = doc.elements[i] # Short hand for easier reading
      
      @paper = Paper.new
      @paper.anthology_id = id + '-' + p.attributes["id"] # D13-1001
      @paper.title = p.elements['title'].text
      
      p.elements.each('author') do |author|
        first_name = ""
        last_name = ""
        full_name = ""
        if author.elements['first'] || author.elements['last']# Check if there are first,last name tags 
          first_name = author.elements['first'].text 	if author.elements['first']
          last_name = author.elements['last'].text	if author.elements['last']
          first_name = "" if first_name == nil
          last_name = "" if last_name == nil
          full_name = first_name + " " + last_name
        else # If not, manually split the name into first name, last name
          full_name = author.text
          first_name, last_name = parse_name(full_name)
        end
        @author = Person.find_or_create_by_first_name_and_last_name_and_full_name(first_name, last_name, full_name)
        @paper.people << @author # Save join paper - person(author) to database
      end
      
      @paper.month 		= p.elements['month'].text			if p.elements['month']
      if p.elements['year']
        @paper.year 	= (p.elements['year'].text).to_i
      else
        @paper.year 	= ("20" + id[1..3]).to_i if id[1..3].to_i < 20
        @paper.year 	= ("19" + id[1..3]).to_i if id[1..3].to_i > 60
      end
      @paper.address 		= p.elements['address'].text		if p.elements['address']
      @paper.publisher 	= p.elements['publisher'].text		if p.elements['publisher']
      @paper.pages 		= p.elements['pages'].text			if p.elements['pages']
      @paper.url 			= "http://aclweb.org/anthology/" + @paper.anthology_id
      if p.attributes["href"] # There is an external link for this paper
        @paper.url = p.attributes["href"]
      end
      if p.elements['doi'] # There is a registered DOI for this paper
        @paper.doi = p.elements['doi'].text
      end


      #			if p.elements['mrf'] # There is a machine readable layer for this paper
      #				@paper.layers 		= "MRF"
      #				@paper.mrf 			= p.elements['mrf'].text
      #			end
      if p.elements['mrf'] # There is a machine readable layer for this paper
        p.elements
      end
      @paper.bibtype 		= p.elements['bibtype'].text		if p.elements['bibtype']
      @paper.bibkey 		= p.elements['bibkey'].text			if p.elements['bibkey']
      
      ['attachment', 'dataset', 'software'].each do |attach_type|
        p.elements.each(attach_type) do |at|
          attachment = Attachment.new
          attachment.name 		= at.text
          attachment.attach_type  = at.attributes['type'] || attach_type
          attachment.url 			= at.attributes['href'] || "http://anthology.aclweb.org/attachments/#{attachment.name[0]}/#{attachment.name[0..2]}/#{attachment.name}"
          attachment.internal 	= !at.attributes['href'] # convert nil to true and value to false
          
          @paper.attachments << attachment
        end
      end
      
      @curr_volume.papers << @paper
      
      if p.elements['revision']
        p.elements.each('revision') do |rev|
          @rev = Revision.new
          @rev.ver = rev.attributes["id"]
          @rev.title = rev.text
          
          @paper.revisions << @rev
        end
      end
    end
    counter += 1
  end
end

def load_sigs(yaml_data)
  yml = YAML::load(yaml_data)
  @sig = Sig.new
  @sig.name	= yml["Name"]
  @sig.sigid	= yml["ShortName"]
  @sig.url	= yml["URL"]
  @sig.save
  yml["Meetings"].each do |meeting|
    keys = meeting.keys
    keys.each do |key|
      meeting[key].each do |anthology_id|
        if anthology_id.is_a? String
          @vol = Volume.find_by_anthology_id(anthology_id[0..-4])
          # anthology_id of volumes with bib_type is stored differently, with last 00 stripped (for workshops)
          @vol_bib = Volume.find_by_anthology_id(anthology_id[0..-3])
          if @vol
            @sig.volumes << @vol
          elsif @vol_bib
            @sig.volumes << @vol_bib
          end
        end
      end
    end
  end
end

def create_venues()
  String hash = File.read("db/venues.txt")
  venues = eval("{#{hash}}")
  
  venues.each do |acronym, venue|
    name = venue.split(':')[0]
    venue_type = venue.split(':')[1]
    Venue.create(acronym: acronym, name: name, venue_type: venue_type)
  end
end

def read_workshops_hash()
  puts "Loading workshop hash..."
  String hash = File.read("db/ws_map.txt")
  return eval("{#{hash}}")
end

def read_joint_meetings_hash()
  puts "Loading joint meetings hash..."
  String hash = File.read("db/joint_map.txt")
  return eval("{#{hash}}")
end

def codes
  ['A', 'C', 'D', 'E', 'F', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'W', 'X', 'Y']
end

def years
  ('65'..'99').to_a + ('00'..'15').to_a
end

namespace :import do
  desc "Import a xml file into the database"
  task :xml, [:local,:volume_anthology] => :environment do |t, args|
    if args[:volume_anthology] == nil # Ingesting the full database
      # Delete everything from the old database
      conn = ActiveRecord::Base.connection
      conn.execute("TRUNCATE TABLE people RESTART IDENTITY;")
      conn.execute("TRUNCATE TABLE people_volumes RESTART IDENTITY;")
      conn.execute("TRUNCATE TABLE papers RESTART IDENTITY;")
      conn.execute("TRUNCATE TABLE attachments RESTART IDENTITY;")
      conn.execute("TRUNCATE TABLE papers_people RESTART IDENTITY;")
      conn.execute("TRUNCATE TABLE volumes RESTART IDENTITY;")
      
      # Ingest the new volumes
      if args[:local] == "true"
        puts "Seeding all volumes from local directory 'import'. Click Ctrl+C if you want to stop..."
        codes.each do |c|
          years.each do |y|
            file_path = "import/#{c+y}.xml"
            if File.exist?(file_path)
              puts "Seeding: #{file_path}"
              String xml_data = File.read(file_path)
              load_volume_xml(xml_data)
            end
          end
        end
        
      else
        puts "Seeding all volumes from anthology website. Click Ctrl+C if you want to stop..."
        codes.each do |c|
          years.each do |y|
            url_string = "http://aclweb.org/anthology/" + c + '/' + c + y + '/' + c + y + ".xml"
            url = URI.parse(url_string)
            request = Net::HTTP.new(url.host, url.port)
            response = request.request_head(url.path)
            if response.kind_of?(Net::HTTPOK)
              puts "Seeding: " + url_string	
              String xml_data = Net::HTTP.get_response(url).body
              load_volume_xml(xml_data)
            else
              puts "Error connecting to #{url_string}"
            end
          end
        end
      end
    elsif args[:volume_anthology].length == 3 # Ingesting a single volume
      puts "Seeding individual volume: #{args[:volume_anthology]}."
      # Delete the old records of the volume and the join tables
      current_volume = "SELECT id FROM volumes WHERE anthology_id LIKE '#{args[:volume_anthology]}%'"
      current_papers = "SELECT id FROM papers WHERE volume_id IN (#{current_volume})"
      conn = ActiveRecord::Base.connection
      conn.execute("DELETE FROM events_volumes WHERE volume_id IN (#{current_volume});")
      conn.execute("DELETE FROM sigs_volumes WHERE volume_id IN (#{current_volume});")
      conn.execute("DELETE FROM people_volumes WHERE volume_id IN (#{current_volume});")
      conn.execute("DELETE FROM attachments WHERE paper_id IN (#{current_papers});")
      conn.execute("DELETE FROM papers_people WHERE paper_id IN (#{current_papers});")
      conn.execute("DELETE FROM papers WHERE volume_id IN (#{current_volume});")
      conn.execute("DELETE FROM volumes WHERE id IN (#{current_volume});")
      
      # If true passed as args, search for file locally and seed
      if args[:local] == "true"
        file_path = "import/" + args[:volume_anthology] + ".xml"
        if File.exist?(file_path)
          puts "Seeding: #{file_path}"
          String xml_data = File.read(file_path)
          load_volume_xml(xml_data)
        else
          puts "No xml found at location: #{file_path}"
        end
        # If no args passed, look online for volume
      else
        c = args[:volume_anthology][0]
        y = args[:volume_anthology][1..2]
        url_string = "http://aclweb.org/anthology/" + c + '/' + c + y + '/' + c + y + ".xml"
        url = URI.parse(url_string)
        request = Net::HTTP.new(url.host, url.port)
        response = request.request_head(url.path)
        if response.kind_of?(Net::HTTPOK)
          puts "Seeding: " + url_string	
          String xml_data = Net::HTTP.get_response(URI.parse(url_string)).body
          load_volume_xml(xml_data)
        else
          puts "Error connecting to #{url_string}"
        end
      end
    else # Wrong input from user
      puts "Invalid rake task! Please read the wiki docs for more info...\n\n"
      puts "To ingest all xml files from local:\n$ rake import:xml[true]"
      puts "To ingest a single file, add anthology_id as args:\n$ rake import:xml[true,C92]"
    end
  end
end

namespace :import do
  desc "Recreates the sigs"
  task :sigs, [:local] => :environment do |t, args|
    puts "Seeding SIGs..."
    # Delete old SIGs table and the sigs_volumes realationship
    conn = ActiveRecord::Base.connection
    conn.execute("TRUNCATE TABLE sigs_volumes;")
    conn.execute("TRUNCATE TABLE sigs RESTART IDENTITY;")
    
    sigs = ['sigann', 'sigbiomed', 'sigdat', 'sigdial', 'sigfsm', 'siggen', 'sighan', 'sighum', 'siglex', 
            'sigmedia', 'sigmol', 'sigmt', 'signll', 'sigparse', 'sigmorphon', 'sigslav', 'sigsem', 'semitic', 'sigslpat', 'sigur', 'sigwac']
    
    if args[:local] == "true"
      puts "Using local import."
      sigs.each do |sig|
        file_path = "import/#{sig}.yaml"
        if File.exist?(file_path)
          puts "Seeding: #{file_path}"
          String yaml_data = File.read(file_path)
          load_sigs(yaml_data)
        else
          puts "Could not find #{file_path}"
        end
      end
    else
      puts "Using online import."
      sigs.each do |sig|
        # Changed URL to temporary staging server
        url_string = "http://69.195.124.161/~aclwebor/anthology//#{sig}.yaml"
        url = URI.parse(url_string)
        request = Net::HTTP.new(url.host, url.port)
        response = request.request_head(url.path)
        if response.kind_of?(Net::HTTPOK)
          puts "Seeding: " + url_string
          String yaml_data = Net::HTTP.get_response(url).body
          load_sigs(yaml_data)
        else
          puts "Error connecting to #{url_string}"
        end
      end
    end
    puts "Done seeding SIGs."
  end
end

namespace :import do
  desc "Recreates the venues"
  task :venues => :environment do |t, args|
    puts "Seeding Venues..."
    # Delte old Venues and reset count of id
    conn = ActiveRecord::Base.connection
    conn.execute("TRUNCATE TABLE venues RESTART IDENTITY;")
    
    create_venues()
    puts "Done seeding Venues."
  end
end

namespace :import do
  desc "Recreates the events"
  task :events => :environment do |t, args|
    puts "Seeding Events..."
    # Delete old Events table and the sigs_volumes realationship
    conn = ActiveRecord::Base.connection
    conn.execute("TRUNCATE TABLE events_volumes;")
    conn.execute("TRUNCATE TABLE events RESTART IDENTITY;")
    
    default_map = { 'A' => "ANLP", # ACL events
      'C' => "COLING", # Non-ACL events
      'D' => "EMNLP", # ACL events
      'E' => "EACL", # ACL events
      'F' => "JEP/TALN/RECITAL", # ACL events
      'H' => "HLT", # Non-ACL events
      'I' => "IJCNLP", # Non-ACL events
      'J' => "CL", # ACL events
      'K' => "CONLL", # ACL events
      'L' => "LREC", # Non-ACL events
      'M' => "MUC", # Non-ACL events
      'N' => "NAACL", # ACL events
      'O' => "ROCLING/IJCLCLP", # Non-ACL events
      'P' => "ACL", # ACL events
      'Q' => "TACL", # ACL events
      'R' => "RANLP", # Non-ACL events
      'S' => "*SEMEVAL", # ACL events
      'T' => "TINLAP", # Non-ACL events
      'U' => "ALTA", # Non-ACL events
      'X' => "TIPSTER", # Non-ACL events
      'Y' => "PACLIC", # Non-ACL events
    }
    ws_map = read_workshops_hash()
    joint_map = read_joint_meetings_hash()
    
    @volumes = Volume.all
    
    @volumes.each do |volume|
      venues = []
      
      volume_anthology = volume.anthology_id
      # Default volume mappings
      if default_map[volume_anthology[0]]
        venues << Venue.find_by_acronym(default_map[volume_anthology[0]])
      end
      
      # Joint meeting venues
      if joint_map[volume_anthology]
        joint_map[volume_anthology].split.each do |acronym|
          venues << Venue.find_by_acronym(acronym)
        end
      end
      
      # Workshop mappings
      if (volume_anthology[0] == 'W' && ws_map[volume_anthology])
        ws_map[volume_anthology].split.each do |acronym|
          venues << Venue.find_by_acronym(acronym)
        end
      end
      
      venues.each do |venue|
        print "volume/venue #{volume.anthology_id} "
	print "#{venue.id}"
        if venue.id
          year = ("20" + volume_anthology[1..2]).to_i if volume_anthology[1..2].to_i < 20
          year = ("19" + volume_anthology[1..2]).to_i if volume_anthology[1..2].to_i > 60
          @event = Event.where(venue_id: venue.id, year: year).first_or_create
          @event.volumes << volume
          puts "Saved #{volume.anthology_id} in #{venue.acronym} (#{year}) "
        end
      end
    end
    puts "Done seeding Events."
    # Clears the cache
    Rake::Task["cache:expire"].invoke
  end
end
