class StaticPagesController < ApplicationController
  def show
    render params[:id]
  end
end
