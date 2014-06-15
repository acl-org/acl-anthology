class AddMrfToPapers < ActiveRecord::Migration
  def change
    add_column :papers, :mrf, :string
  end
end
