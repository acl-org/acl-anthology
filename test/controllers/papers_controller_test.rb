require 'test_helper'

class PapersControllerTest < ActionController::TestCase
  setup do
    @paper = papers(:one)
  end

  test "should get index" do
    get :index
    assert_response :success
    assert_not_nil assigns(:papers)
  end

  test "should get new" do
    get :new
    assert_response :success
  end

  test "should create paper" do
    assert_difference('Paper.count') do
      post :create, paper: { address: @paper.address, bibkey: @paper.bibkey, bibtype: @paper.bibtype, month: @paper.month, pages: @paper.pages, paper_id: @paper.paper_id, publisher: @paper.publisher, title: @paper.title, url: @paper.url, volume_id: @paper.volume_id, year: @paper.year }
    end

    assert_redirected_to paper_path(assigns(:paper))
  end

  test "should show paper" do
    get :show, id: @paper
    assert_response :success
  end

  test "should get edit" do
    get :edit, id: @paper
    assert_response :success
  end

  test "should update paper" do
    patch :update, id: @paper, paper: { address: @paper.address, bibkey: @paper.bibkey, bibtype: @paper.bibtype, month: @paper.month, pages: @paper.pages, paper_id: @paper.paper_id, publisher: @paper.publisher, title: @paper.title, url: @paper.url, volume_id: @paper.volume_id, year: @paper.year }
    assert_redirected_to paper_path(assigns(:paper))
  end

  test "should destroy paper" do
    assert_difference('Paper.count', -1) do
      delete :destroy, id: @paper
    end

    assert_redirected_to papers_path
  end
end
