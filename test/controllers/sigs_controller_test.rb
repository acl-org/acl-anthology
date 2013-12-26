require 'test_helper'

class SigsControllerTest < ActionController::TestCase
  setup do
    @sig = sigs(:one)
  end

  test "should get index" do
    get :index
    assert_response :success
    assert_not_nil assigns(:sigs)
  end

  test "should get new" do
    get :new
    assert_response :success
  end

  test "should create sig" do
    assert_difference('Sig.count') do
      post :create, sig: { name: @sig.name, sigid: @sig.sigid, url: @sig.url }
    end

    assert_redirected_to sig_path(assigns(:sig))
  end

  test "should show sig" do
    get :show, id: @sig
    assert_response :success
  end

  test "should get edit" do
    get :edit, id: @sig
    assert_response :success
  end

  test "should update sig" do
    patch :update, id: @sig, sig: { name: @sig.name, sigid: @sig.sigid, url: @sig.url }
    assert_redirected_to sig_path(assigns(:sig))
  end

  test "should destroy sig" do
    assert_difference('Sig.count', -1) do
      delete :destroy, id: @sig
    end

    assert_redirected_to sigs_path
  end
end
