class AddVolumeIssueToPapers < ActiveRecord::Migration
  def change
    add_column :papers, :journal_volume, :string
    add_column :papers, :issue, :string
  end
end
