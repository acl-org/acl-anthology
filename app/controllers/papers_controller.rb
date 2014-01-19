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
    mods_xml= generate_modsxml(@paper.title, @paper.year, @paper.volume.title, @paper.people)
    file = File.new("bibexport/paper#{@paper.id}mods.xml",'w')
    file.write mods_xml
    file.close
    bib=`xml2bib bibexport/paper#{@paper.id}mods.xml`
    ris=`xml2ris bibexport/paper#{@paper.id}mods.xml`
    endf =`xml2end bibexport/paper#{@paper.id}mods.xml`
    word=`xml2wordbib bibexport/paper#{@paper.id}mods.xml`
    dblp= `ruby bibscript/xml2dblp.rb bibexport/paper#{@paper.id}mods.xml`
    respond_to do |format|
      format.xml { render xml: mods_xml }
      format.bib { send_data bib, :filename => "paper#{@paper.id}.bib" }
      format.ris { send_data ris, :filename => "paper#{@paper.id}.ris" }
      format.endf { send_data endf, :filename => "paper#{@paper.id}.end" }
      format.text { send_data dblp, :filename => "paper#{@paper.id}.txt" }
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

    def generate_modsxml paper_title,year,volume_title,authors
      require "rexml/document"
      xml = REXML::Document.new "<?xml version='1.0'?>"
      mods=xml.add_element 'mods'
      mods.attributes["ID"]='d1ej'
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
      origin_info = mods.add_element 'originInfo'
      date_issued = origin_info.add_element 'dateIssued'
      date_issued.text = year

      genre_type = mods.add_element 'genre'
      genre_type.text = "conference publication"

      related_item = mods.add_element 'relatedItem'
      related_item.attributes["type"]="host"
      volume_info = related_item.add_element 'titleInfo'
      volume_name = volume_info.add_element 'title'
      volume_name.text = volume_title
      return xml.to_s
    end
  end
