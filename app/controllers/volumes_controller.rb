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
    mods_xml = generate_volume_modsxml(@volume.title, @volume.year, @editors)
    file = File.new("bibexport/volume#{@volume.id}mods.xml",'w')
    file.write mods_xml
    file.close
    bib=`xml2bib bibexport/volume#{@volume.id}mods.xml`
    ris=`xml2ris bibexport/volume#{@volume.id}mods.xml`
    endf =`xml2end bibexport/volume#{@volume.id}mods.xml`
    word=`xml2wordbib bibexport/volume#{@volume.id}mods.xml`
    dblp= `ruby bibscript/xml2dblp.rb bibexport/paper#{@paper.id}mods.xml`
    respond_to do |format|
      format.xml { render xml: mods_xml }
      format.bib { send_data bib, :filename => "volume#{@volume.id}.bib" }
      format.ris { send_data ris, :filename => "volume#{@volume.id}.ris" }
      format.endf { send_data endf, :filename => "volume#{@volume.id}.end" }
      format.text { send_data dblp, :filename => "paper#{@paper.id}.txt" }
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

    def generate_volume_modsxml paper_title,year,authors
      require "rexml/document"
      xml = REXML::Document.new "<?xml version='1.0'?>"
      mods=xml.add_element 'mods'
      mods.attributes["ID"]='d1ej'
      title_info = mods.add_element 'titleInfo'
      title_name = title_info.add_element 'title'
      title_name.text = paper_title
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
      date_issued = origin_info.add_element 'dateIssued'
      date_issued.text = year

      return xml.to_s
    end
  end
