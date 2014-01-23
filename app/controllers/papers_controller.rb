class PapersController < ApplicationController
  before_action :set_paper, only: [:show, :edit, :update, :destroy]

  # GET /papers
  # GET /papers.json
  def index
    @papers = Paper.all.page(params[:page])
  end

  # GET /papers/1
  # GET /papers/1.json
  def show
    set_paper
    @in_volume = Volume.find(@paper.volume_id)
    @authors = @paper.people

    @events = @in_volume.events
    @sigs = @in_volume.sigs
  end

  # GET /papers/new
  def new
    @paper = Paper.new
  end

  # GET /papers/1/edit
  def edit
  end

  # POST /papers
  # POST /papers.json
  def create
    @paper = Paper.new(paper_params)

    respond_to do |format|
      if @paper.save
        format.html { redirect_to @paper, notice: 'Paper was successfully created.' }
        format.json { render action: 'show', status: :created, location: @paper }
      else
        format.html { render action: 'new' }
        format.json { render json: @paper.errors, status: :unprocessable_entity }
      end
    end
  end

  # PATCH/PUT /papers/1
  # PATCH/PUT /papers/1.json
  def update
    respond_to do |format|
      if @paper.update(paper_params)
        format.html { redirect_to @paper, notice: 'Paper was successfully updated.' }
        format.json { head :no_content }
      else
        format.html { render action: 'edit' }
        format.json { render json: @paper.errors, status: :unprocessable_entity }
      end
    end
  end

  # DELETE /papers/1
  # DELETE /papers/1.json
  def destroy
    @paper.destroy
    respond_to do |format|
      format.html { redirect_to papers_url }
      format.json { head :no_content }
    end
  end

  def bibexport
    set_paper
    @authors = @paper.people
    mods_xml= generate_modsxml(@paper)
    file = File.new("bibexport/#{@paper.anthology_id}.xml",'w')
    file.write mods_xml
    file.close
    bib=`xml2bib bibexport/#{@paper.anthology_id}.xml bibexport/#{@paper.anthology_id}.bib`
    ris=`xml2ris bibexport/#{@paper.anthology_id}.xml bibexport/#{@paper.anthology_id}.ris`
    endf =`xml2end bibexport/#{@paper.anthology_id}.xml bibexport/#{@paper.anthology_id}.endf`
    word=`xml2wordbib bibexport/#{@paper.anthology_id}.xml bibexport/#{@paper.anthology_id}.word`
    dblp= `ruby lib/bibscript/xml2dblp.rb bibexport/#{@paper.anthology_id}.xml`
    acm   = `ruby lib/bibscript/xml2acm.rb bibexport/#{@paper.anthology_id}.xml`
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
    def set_paper
      @paper = Paper.find(params[:id])
    end

    # Never trust parameters from the scary internet, only allow the white list through.
    def paper_params
      params.require(:paper).permit(:volume_id, :anthology_id, :title, :month, :year, :address, :publisher, :pages, :url, :bibtype, :bibkey, :attachment, :attach_type)
    end

    def generate_modsxml paper
      dash = "–"
      require "rexml/document"
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
          paper_address = paper_location.add_element 'physicalAddress'
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
      return xml.to_s
    end
  end
