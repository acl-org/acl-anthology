class PapersController < ApplicationController
  before_action :set_paper, only: [:show, :edit, :update, :destroy]
  authorize_resource

  # GET /papers
  # GET /papers.json
  def index
    @papers = Paper.all.page(params[:page])
  end

  # GET /papers/1
  # GET /papers/1.json
  def show
    set_paper
    
    respond_to do |format|
      format.xml { send_data(File.read("export/mods/#{@paper.anthology_id}.xml"), :type => 'text/xml', :disposition => 'inline')}
      format.bib { send_data(File.read("export/bib/#{@paper.anthology_id}.bib"), :type => 'text/plain', :disposition => 'inline')}
      format.ris { send_data(File.read("export/ris/#{@paper.anthology_id}.ris"), :type => 'text/plain', :disposition => 'inline')}
      format.endf { send_data(File.read("export/endf/#{@paper.anthology_id}.endf"), :type => 'text/plain', :disposition => 'inline')}
      format.word { send_data(File.read("export/word/#{@paper.anthology_id}.word"), :type => 'text/plain', :disposition => 'inline')}
      format.dblp { send_data(File.read("export/dblp/#{@paper.anthology_id}.html"), :type => 'text/html', :disposition => 'inline')}
      # format.acm { send_data(File.read("export/acm/#{@paper.anthology_id}.acm"), :type => 'text/html', :disposition => 'inline')}
      format.all {}
    end
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

  private
    # Use callbacks to share common setup or constraints between actions.
    def set_paper
      @paper = Paper.friendly.find(params[:id])
    end

    # Never trust parameters from the scary internet, only allow the white list through.
    def paper_params
      params.require(:paper).permit(:volume_id, :anthology_id, :title, :month, :year, :address, :publisher, :pages, :url, :bibtype, :bibkey, :attachment, :attach_type)
    end
  end
