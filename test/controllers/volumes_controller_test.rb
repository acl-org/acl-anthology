require 'test_helper'

class VolumesControllerTest < ActionController::TestCase
  setup do
    @volume = volumes(:one)
  end

  test "should get index" do
    get :index
    assert_response :success
    assert_not_nil assigns(:volumes)
  end

  test "should get new" do
    get :new
    assert_response :success
  end

  test "should create volume" do
    assert_difference('Volume.count') do
      post :create, volume: { acronym: @volume.acronym, address: @volume.address, bibkey: @volume.bibkey, bibtype: @volume.bibtype, month: @volume.month, publisher: @volume.publisher, title: @volume.title, url: @volume.url, anthology_id: @volume.anthology_id, year: @volume.year }
    end

    assert_redirected_to volume_path(assigns(:volume))
  end

  test "should show volume" do
    get :show, id: @volume
    assert_response :success
  end

  test "should get edit" do
    get :edit, id: @volume
    assert_response :success
  end

  test "should update volume" do
    patch :update, id: @volume, volume: { acronym: @volume.acronym, address: @volume.address, bibkey: @volume.bibkey, bibtype: @volume.bibtype, month: @volume.month, publisher: @volume.publisher, title: @volume.title, url: @volume.url, anthology_id: @volume.anthology_id, year: @volume.year }
    assert_redirected_to volume_path(assigns(:volume))
  end

  test "should destroy volume" do
    assert_difference('Volume.count', -1) do
      delete :destroy, id: @volume
    end

    assert_redirected_to volumes_path
  end
end
