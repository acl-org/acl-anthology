class PeopleController < ApplicationController
  before_action :set_person, only: [:show, :edit, :update, :destroy]

  # GET /people
  # GET /people.json
  def index
    @people = Person.all.page(params[:page])
  end

  # GET /people/1
  # GET /people/1.json
  def show
    set_person
    @papers = @person.papers
    @volumes = @person.volumes

    # For showing the publications of a person sorted by year
    @years = []
    @all_co_authors = []
    @all_venues = []
    @papers.each do |paper|
      unless @years.include?(paper.year)
        @years << paper.year
      end

      paper.people.each do |author|
        unless author == @person
          @all_co_authors << author
        end
      end

      @in_volume = Volume.find(paper.volume_id)
      @in_volume.events.each do |event|
        @all_venues << Venue.find(event.venue_id)
      end
    end
    @years = @years.sort.reverse

    # For showing co-authors of the person
    @co_authors = Hash.new(0)
    @all_co_authors.each do |au|
      @co_authors[au] += 1
    end
    @co_authors = @co_authors.sort_by{|au,count| -count}[0..9]

    # For showing co-authors of the person
    @venues = Hash.new(0)
    @all_venues.each do |v|
      @venues[v] += 1
    end
    @venues = @venues.sort_by{|v,count| -count}[0..7]
  end

  # GET /people/new
  def new
    @person = Person.new
  end

  # GET /people/1/edit
  def edit
  end

  # POST /people
  # POST /people.json
  def create
    @person = Person.new(person_params)

    respond_to do |format|
      if @person.save
        format.html { redirect_to @person, notice: 'Person was successfully created.' }
        format.json { render action: 'show', status: :created, location: @person }
      else
        format.html { render action: 'new' }
        format.json { render json: @person.errors, status: :unprocessable_entity }
      end
    end
  end

  # PATCH/PUT /people/1
  # PATCH/PUT /people/1.json
  def update
    respond_to do |format|
      if @person.update(person_params)
        format.html { redirect_to @person, notice: 'Person was successfully updated.' }
        format.json { head :no_content }
      else
        format.html { render action: 'edit' }
        format.json { render json: @person.errors, status: :unprocessable_entity }
      end
    end
  end

  # DELETE /people/1
  # DELETE /people/1.json
  def destroy
    @person.destroy
    respond_to do |format|
      format.html { redirect_to people_url }
      format.json { head :no_content }
    end
  end

  private
    # Use callbacks to share common setup or constraints between actions.
    def set_person
      @person = Person.find(params[:id])
    end

    # Never trust parameters from the scary internet, only allow the white list through.
    def person_params
      params.require(:person).permit(:person_id, :first_name, :last_name, :full_name)
    end
end
