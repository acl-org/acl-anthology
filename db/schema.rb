# encoding: UTF-8
# This file is auto-generated from the current state of the database. Instead
# of editing this file, please use the migrations feature of Active Record to
# incrementally modify your database, and then regenerate this schema definition.
#
# Note that this schema.rb definition is the authoritative source for your
# database schema. If you need to create the application database on another
# system, you should be using db:schema:load, not running all the migrations
# from scratch. The latter is a flawed and unsustainable approach (the more migrations
# you'll amass, the slower it'll run and the greater likelihood for issues).
#
# It's strongly recommended that you check this file into your version control system.

ActiveRecord::Schema.define(version: 20161001162215) do

  # These are extensions that must be enabled in order to support this database
  enable_extension "plpgsql"

  create_table "attachments", force: true do |t|
    t.string   "name"
    t.string   "attach_type"
    t.boolean  "internal"
    t.text     "url"
    t.integer  "paper_id"
    t.datetime "created_at"
    t.datetime "updated_at"
  end

  add_index "attachments", ["paper_id"], name: "index_attachments_on_paper_id", using: :btree

  create_table "bookmarks", force: true do |t|
    t.integer  "user_id",     null: false
    t.string   "document_id"
    t.string   "title"
    t.datetime "created_at"
    t.datetime "updated_at"
    t.string   "user_type"
  end

  create_table "events", force: true do |t|
    t.integer  "year"
    t.integer  "venue_id"
    t.string   "kind"
    t.datetime "created_at"
    t.datetime "updated_at"
    t.string   "slug"
  end

  add_index "events", ["slug"], name: "index_events_on_slug", unique: true, using: :btree

  create_table "events_volumes", id: false, force: true do |t|
    t.integer "event_id"
    t.integer "volume_id"
  end

  create_table "friendly_id_slugs", force: true do |t|
    t.text     "slug",                      null: false
    t.integer  "sluggable_id",              null: false
    t.string   "sluggable_type", limit: 50
    t.string   "scope"
    t.datetime "created_at"
  end

  add_index "friendly_id_slugs", ["slug", "sluggable_type", "scope"], name: "index_friendly_id_slugs_on_slug_and_sluggable_type_and_scope", unique: true, using: :btree
  add_index "friendly_id_slugs", ["slug", "sluggable_type"], name: "index_friendly_id_slugs_on_slug_and_sluggable_type", using: :btree
  add_index "friendly_id_slugs", ["sluggable_id"], name: "index_friendly_id_slugs_on_sluggable_id", using: :btree
  add_index "friendly_id_slugs", ["sluggable_type"], name: "index_friendly_id_slugs_on_sluggable_type", using: :btree

  create_table "papers", force: true do |t|
    t.integer  "volume_id"
    t.string   "anthology_id"
    t.text     "title"
    t.string   "month"
    t.integer  "year"
    t.string   "address"
    t.string   "publisher"
    t.string   "pages"
    t.string   "url"
    t.string   "bibtype"
    t.string   "bibkey"
    t.datetime "created_at"
    t.datetime "updated_at"
    t.text     "slug"
    t.string   "mrf"
    t.string   "layers"
    t.string   "doi"
  end

  add_index "papers", ["slug"], name: "index_papers_on_slug", unique: true, using: :btree

  create_table "papers_people", id: false, force: true do |t|
    t.integer "paper_id"
    t.integer "person_id"
  end

  create_table "people", force: true do |t|
    t.string   "first_name"
    t.string   "last_name"
    t.string   "full_name"
    t.datetime "created_at"
    t.datetime "updated_at"
    t.string   "slug"
  end

  add_index "people", ["slug"], name: "index_people_on_slug", unique: true, using: :btree

  create_table "people_volumes", id: false, force: true do |t|
    t.integer "person_id"
    t.integer "volume_id"
  end

  create_table "revisions", force: true do |t|
    t.integer  "paper_id"
    t.integer  "ver"
    t.string   "title"
    t.datetime "created_at"
    t.datetime "updated_at"
  end

  create_table "roles", force: true do |t|
    t.string   "name"
    t.integer  "resource_id"
    t.string   "resource_type"
    t.datetime "created_at"
    t.datetime "updated_at"
  end

  add_index "roles", ["name", "resource_type", "resource_id"], name: "index_roles_on_name_and_resource_type_and_resource_id", using: :btree
  add_index "roles", ["name"], name: "index_roles_on_name", using: :btree

  create_table "searches", force: true do |t|
    t.text     "query_params"
    t.integer  "user_id"
    t.datetime "created_at"
    t.datetime "updated_at"
    t.string   "user_type"
  end

  add_index "searches", ["user_id"], name: "index_searches_on_user_id", using: :btree

  create_table "sigs", force: true do |t|
    t.string   "name"
    t.string   "sigid"
    t.string   "url"
    t.datetime "created_at"
    t.datetime "updated_at"
    t.string   "slug"
  end

  add_index "sigs", ["slug"], name: "index_sigs_on_slug", unique: true, using: :btree

  create_table "sigs_volumes", id: false, force: true do |t|
    t.integer "sig_id"
    t.integer "volume_id"
  end

  create_table "users", force: true do |t|
    t.string   "email",                  default: "",    null: false
    t.string   "encrypted_password",     default: "",    null: false
    t.string   "reset_password_token"
    t.datetime "reset_password_sent_at"
    t.datetime "remember_created_at"
    t.integer  "sign_in_count",          default: 0,     null: false
    t.datetime "current_sign_in_at"
    t.datetime "last_sign_in_at"
    t.string   "current_sign_in_ip"
    t.string   "last_sign_in_ip"
    t.datetime "created_at"
    t.datetime "updated_at"
    t.boolean  "guest",                  default: false
  end

  add_index "users", ["email"], name: "index_users_on_email", unique: true, using: :btree
  add_index "users", ["reset_password_token"], name: "index_users_on_reset_password_token", unique: true, using: :btree

  create_table "users_roles", id: false, force: true do |t|
    t.integer "user_id"
    t.integer "role_id"
  end

  add_index "users_roles", ["user_id", "role_id"], name: "index_users_roles_on_user_id_and_role_id", using: :btree

  create_table "venues", force: true do |t|
    t.string   "acronym"
    t.string   "name"
    t.string   "venue_type"
    t.datetime "created_at"
    t.datetime "updated_at"
    t.string   "slug"
  end

  add_index "venues", ["slug"], name: "index_venues_on_slug", unique: true, using: :btree

  create_table "volumes", force: true do |t|
    t.string   "anthology_id"
    t.string   "acronym"
    t.string   "title"
    t.string   "month"
    t.integer  "year"
    t.string   "address"
    t.string   "publisher"
    t.string   "url"
    t.string   "bibtype"
    t.string   "bibkey"
    t.datetime "created_at"
    t.datetime "updated_at"
    t.string   "slug"
    t.string   "journal_name"
    t.string   "journal_volume"
    t.string   "journal_issue"
  end

  add_index "volumes", ["slug"], name: "index_volumes_on_slug", unique: true, using: :btree

end
