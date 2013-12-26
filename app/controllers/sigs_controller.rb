class SigsController < ApplicationController
  before_action :set_sig, only: [:show, :edit, :update, :destroy]

  # GET /sigs
  # GET /sigs.json
  def index
    @sigs = Sig.all
  end

  # GET /sigs/1
  # GET /sigs/1.json
  def show
  end

  # GET /sigs/new
  def new
    @sig = Sig.new
  end

  # GET /sigs/1/edit
  def edit
  end

  # POST /sigs
  # POST /sigs.json
  def create
    @sig = Sig.new(sig_params)

    respond_to do |format|
      if @sig.save
        format.html { redirect_to @sig, notice: 'Sig was successfully created.' }
        format.json { render action: 'show', status: :created, location: @sig }
      else
        format.html { render action: 'new' }
        format.json { render json: @sig.errors, status: :unprocessable_entity }
      end
    end
  end

  # PATCH/PUT /sigs/1
  # PATCH/PUT /sigs/1.json
  def update
    respond_to do |format|
      if @sig.update(sig_params)
        format.html { redirect_to @sig, notice: 'Sig was successfully updated.' }
        format.json { head :no_content }
      else
        format.html { render action: 'edit' }
        format.json { render json: @sig.errors, status: :unprocessable_entity }
      end
    end
  end

  # DELETE /sigs/1
  # DELETE /sigs/1.json
  def destroy
    @sig.destroy
    respond_to do |format|
      format.html { redirect_to sigs_url }
      format.json { head :no_content }
    end
  end

  private
    # Use callbacks to share common setup or constraints between actions.
    def set_sig
      @sig = Sig.find(params[:id])
    end

    # Never trust parameters from the scary internet, only allow the white list through.
    def sig_params
      params.require(:sig).permit(:name, :sigid, :url)
    end
end
