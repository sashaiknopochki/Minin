export default function History() {
  // TODO: Fetch search history data

  return (
    <div className="w-full py-8">
      {/* Page Title */}
      <h1 className="text-4xl font-bold mb-8">Search History</h1>

      {/* Empty state - will be replaced when data fetching is implemented */}
      <div className="flex flex-col items-center justify-center py-16 px-4">
        <p className="text-lg text-muted-foreground text-center">
          No search history yet. Start translating to build your history!
        </p>
      </div>

      {/* Placeholder for table */}
      <div className="mt-8">
        {/* Table will be implemented here when data fetching is added */}
      </div>
    </div>
  );
}