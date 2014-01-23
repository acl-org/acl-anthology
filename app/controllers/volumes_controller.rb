class VolumesController < ApplicationController
  before_action :set_volume, only: [:show, :edit, :update, :destroy]

  # GET /volumes
  # GET /volumes.json
  def index
    @volumes = Volume.all.page(params[:page])
  end

  # GET /volumes/1
  # GET /volumes/1.json
  def show
    set_volume
    # @papers = @volume.papers.page(params[:page]).per(20)
    @papers = @volume.papers
    @editors = @volume.people

    @events = @volume.events
    @sigs = @volume.sigs
    #Kaminari.paginate_array(@volume.papers).page(params[:page]).per(10)
    #@volume.papers = Paper.all.where(:anthology_id => @volume.anthology_id)
  end

  # GET /volumes/new
  def new
    @volume = Volume.new
  end

  # GET /volumes/1/edit
  def edit
  end

  # POST /volumes
  # POST /volumes.json
  def create
    @volume = Volume.new(volume_params)
    respond_to do |format|
      if @volume.save
        format.html { redirect_to @volume, notice: 'Volume was successfully created.' }
        format.json { render action: 'show', status: :created, location: @volume }
      else
        format.html { render action: 'new' }
        format.json { render json: @volume.errors, status: :unprocessable_entity }
      end
    end
  end

  # PATCH/PUT /volumes/1
  # PATCH/PUT /volumes/1.json
  def update
    respond_to do |format|
      if @volume.update(volume_params)
        format.html { redirect_to @volume, notice: 'Volume was successfully updated.' }
        format.json { head :no_content }
      else
        format.html { render action: 'edit' }
        format.json { render json: @volume.errors, status: :unprocessable_entity }
      end
    end
  end

  # DELETE /volumes/1
  # DELETE /volumes/1.json
  def destroy
    @volume.destroy
    respond_to do |format|
      format.html { redirect_to volumes_url }
      format.json { head :no_content }
    end
  end

  def bibexport
    set_volume
    @editors = @volume.people
    mods_xml = generate_volume_modsxml(@volume)
    puts mods_xml
    puts "hey"
    file = File.new("bibexport/#{@volume.anthology_id}.xml",'w')
    file.write mods_xml
    file.close
    bib   =  `xml2bib bibexport/#{@volume.anthology_id}.xml`
    ris   =  `xml2ris bibexport/#{@volume.anthology_id}.xml`
    endf  =  `xml2end bibexport/#{@volume.anthology_id}.xml`
    word  =  `xml2wordbib bibexport/#{@volume.anthology_id}.xml`
    dblp  = `ruby lib/bibscript/xml2dblp.rb bibexport/#{@volume.anthology_id}.xml`
    acm   = `ruby lib/bibscript/xml2acm.rb bibexport/#{@volume.anthology_id}.xml`
    respond_to do |format|
      format.xml { send_data(mods_xml, :type => 'text/xml', :disposition => 'inline')}
      format.bib { send_data(bib, :type => 'text/plain', :disposition => 'inline')}
      format.ris { send_data ris, :type => 'text/plain', :disposition => 'inline' }
      format.endf { send_data endf, :type => 'text/plain', :disposition => 'inline' }
      format.word { send_data word, :type => 'text/plain', :disposition => 'inline'}
      format.dblp { send_data dblp, :type => 'text/html', :disposition => 'inline' }
      format.acm { send_data acm, :type => 'text/html', :disposition => 'inline' }
    end
  end

  private
    # Use callbacks to share common setup or constraints between actions.
    def set_volume
      @volume = Volume.find(params[:id])
    end

    # Never trust parameters from the scary internet, only allow the white list through.
    def volume_params
      params.require(:volume).permit(:anthology_id, :title, :month, :year, :address, :publisher, :url, :bibtype, :bibkey)
    end

    def generate_volume_modsxml volume
      papers = volume.papers
      volume_title = volume.title
      year = volume.year
      authors = volume.people
      require "rexml/document"
      dash = "–"
      xml = REXML::Document.new "<?xml version='1.0'?>"
      mods=xml.add_element 'modsCollection'
      title_info = mods.add_element 'titleInfo'
      title_name = title_info.add_element 'title'
      title_name.text = volume_title
      #add author information
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
        roleterm.text="editor"

      }
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


            paper_genre_type = paper_mods.add_element 'genre'
            if( paper.anthology_id[0] == "W")
              paper_genre_type.text = "workshop publication"
            else
              paper_genre_type.text = "conference publication"
            end

            paper_related_item = paper_mods.add_element 'relatedItem'

            paper_related_item.attributes["type"]="host"
          end
        end
        puts "heo"
        puts xml.to_s
        return xml.to_s
      end
    end
  end


