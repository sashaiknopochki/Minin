import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useSearchParams } from "react-router-dom";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Trash2, Loader2 } from "lucide-react";

interface Phrase {
  id: number;
  text: string;
  language_code: string;
  phrase_type: string;
}

interface SearchHistoryItem {
  id: number;
  phrase: Phrase;
  translations: {
    [languageCode: string]: string;
  };
  searched_at: string;
}

interface PaginationInfo {
  page: number;
  per_page: number;
  total: number;
  pages: number;
}

interface HistoryResponse {
  searches: SearchHistoryItem[];
  pagination: PaginationInfo;
}

export default function History() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [historyData, setHistoryData] = useState<SearchHistoryItem[]>([]);
  const [pagination, setPagination] = useState<PaginationInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingIds, setDeletingIds] = useState<Set<number>>(new Set());

  // Get current page from URL or default to 1
  const currentPage = parseInt(searchParams.get("page") || "1", 10);

  // Get user's active languages for column headers
  const userLanguages = user?.translator_languages || [];
  const primaryLanguage = user?.primary_language_code || "en";

  // Combine all languages (primary + translator languages)
  const allLanguages = [primaryLanguage, ...userLanguages.filter((lang: string) => lang !== primaryLanguage)];

  // Fetch search history
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`/api/history?page=${currentPage}`, {
          method: "GET",
          credentials: "include",
        });

        if (!response.ok) {
          throw new Error("Failed to fetch search history");
        }

        const data: HistoryResponse = await response.json();
        setHistoryData(data.searches || []);
        setPagination(data.pagination);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load history");
      } finally {
        setLoading(false);
      }
    };

    if (user) {
      fetchHistory();
    } else {
      setLoading(false);
    }
  }, [user, currentPage]);

  // Handle page change
  const handlePageChange = (newPage: number) => {
    setSearchParams({ page: newPage.toString() });
  };

  // Handle delete
  const handleDelete = async (searchId: number) => {
    try {
      setDeletingIds(new Set(deletingIds).add(searchId));

      const response = await fetch(`/api/history/${searchId}`, {
        method: "DELETE",
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Failed to delete search");
      }

      // Remove from local state
      setHistoryData(historyData.filter((item) => item.id !== searchId));
    } catch (err) {
      console.error("Delete error:", err);
      alert("Failed to delete search. Please try again.");
    } finally {
      const newDeletingIds = new Set(deletingIds);
      newDeletingIds.delete(searchId);
      setDeletingIds(newDeletingIds);
    }
  };

  // Get language name helper
  const getLanguageName = (code: string) => {
    const languageNames: { [key: string]: string } = {
      en: "English",
      de: "German",
      ru: "Russian",
      es: "Spanish",
      fr: "French",
      it: "Italian",
      pt: "Portuguese",
      zh: "Chinese",
      ja: "Japanese",
      ko: "Korean",
    };
    return languageNames[code] || code.toUpperCase();
  };

  // Format date as DD.MM.YYYY
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}.${month}.${year}`;
  };

  // Loading state
  if (loading) {
    return (
      <div className="w-full py-8">
        <h1 className="text-4xl font-bold mb-8 text-left">History</h1>
        <div className="flex flex-col items-center justify-center py-16 px-4">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-lg text-muted-foreground text-center mt-4">
            Loading your search history...
          </p>
        </div>
      </div>
    );
  }

  // Not logged in
  if (!user) {
    return (
      <div className="w-full py-8">
        <h1 className="text-4xl font-bold mb-8 text-left">History</h1>
        <div className="flex flex-col items-center justify-center py-16 px-4">
          <p className="text-lg text-muted-foreground text-center">
            Please sign in to view your search history.
          </p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="w-full py-8">
        <h1 className="text-4xl font-bold mb-8 text-left">History</h1>
        <div className="flex flex-col items-center justify-center py-16 px-4">
          <p className="text-lg text-destructive text-center">
            {error}
          </p>
        </div>
      </div>
    );
  }

  // Empty state
  if (historyData.length === 0) {
    return (
      <div className="w-full py-8">
        <h1 className="text-4xl font-bold mb-8 text-left">History</h1>
        <div className="flex flex-col items-center justify-center py-16 px-4">
          <p className="text-lg text-muted-foreground text-center">
            No search history yet. Start translating to build your history!
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full py-8">
      {/* Page Title */}
      <h1 className="text-4xl font-bold mb-8 text-left">History</h1>

      {/* Table Container - Responsive with horizontal scroll */}
      <div className="w-full overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {/* Dynamic language columns */}
              {allLanguages.slice(0, 3).map((langCode) => (
                <TableHead key={langCode} className="min-w-[150px]">
                  {getLanguageName(langCode)}
                </TableHead>
              ))}

              {/* Additional columns for desktop - hidden on mobile */}
              {allLanguages.slice(3).map((langCode) => (
                <TableHead key={langCode} className="min-w-[150px] hidden md:table-cell">
                  {getLanguageName(langCode)}
                </TableHead>
              ))}

              {/* Date column */}
              <TableHead className="min-w-[120px]">Date</TableHead>

              {/* Delete column */}
              <TableHead className="w-[80px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {historyData.map((item) => {
              const sourceLanguage = item.phrase.language_code;

              return (
                <TableRow key={item.id}>
                  {/* Dynamic language columns */}
                  {allLanguages.slice(0, 3).map((langCode) => {
                    const isSourceLanguage = langCode === sourceLanguage;
                    const text = isSourceLanguage
                      ? item.phrase.text
                      : item.translations[langCode] || "-";

                    return (
                      <TableCell
                        key={langCode}
                        className={isSourceLanguage ? "font-bold" : ""}
                      >
                        {text}
                      </TableCell>
                    );
                  })}

                  {/* Additional columns for desktop */}
                  {allLanguages.slice(3).map((langCode) => {
                    const isSourceLanguage = langCode === sourceLanguage;
                    const text = isSourceLanguage
                      ? item.phrase.text
                      : item.translations[langCode] || "-";

                    return (
                      <TableCell
                        key={langCode}
                        className={`hidden md:table-cell ${isSourceLanguage ? "font-bold" : ""}`}
                      >
                        {text}
                      </TableCell>
                    );
                  })}

                  {/* Date column */}
                  <TableCell className="text-sm text-muted-foreground text-left">
                    {formatDate(item.searched_at)}
                  </TableCell>

                  {/* Delete button */}
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(item.id)}
                      disabled={deletingIds.has(item.id)}
                      className="h-8 w-8"
                    >
                      {deletingIds.has(item.id) ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* Pagination and Result Count */}
      {pagination && (
        <div className="mt-6 space-y-4">
          {/* Result count display */}
          <div className="text-sm text-muted-foreground text-center">
            Showing {((pagination.page - 1) * pagination.per_page) + 1}-
            {Math.min(pagination.page * pagination.per_page, pagination.total)} of {pagination.total} results
          </div>

          {/* Pagination controls */}
          {pagination.pages > 1 && (
            <Pagination>
              <PaginationContent>
                {/* Previous button */}
                <PaginationItem>
                  <PaginationPrevious
                    onClick={() => handlePageChange(currentPage - 1)}
                    className={currentPage <= 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                  />
                </PaginationItem>

                {/* Page numbers */}
                {(() => {
                  const pages = [];
                  const totalPages = pagination.pages;

                  // Always show first page
                  pages.push(
                    <PaginationItem key={1}>
                      <PaginationLink
                        onClick={() => handlePageChange(1)}
                        isActive={currentPage === 1}
                        className="cursor-pointer"
                      >
                        1
                      </PaginationLink>
                    </PaginationItem>
                  );

                  // Show ellipsis if needed before current page range
                  if (currentPage > 3) {
                    pages.push(
                      <PaginationItem key="ellipsis-start">
                        <PaginationEllipsis />
                      </PaginationItem>
                    );
                  }

                  // Show pages around current page
                  const startPage = Math.max(2, currentPage - 1);
                  const endPage = Math.min(totalPages - 1, currentPage + 1);

                  for (let i = startPage; i <= endPage; i++) {
                    pages.push(
                      <PaginationItem key={i}>
                        <PaginationLink
                          onClick={() => handlePageChange(i)}
                          isActive={currentPage === i}
                          className="cursor-pointer"
                        >
                          {i}
                        </PaginationLink>
                      </PaginationItem>
                    );
                  }

                  // Show ellipsis if needed after current page range
                  if (currentPage < totalPages - 2) {
                    pages.push(
                      <PaginationItem key="ellipsis-end">
                        <PaginationEllipsis />
                      </PaginationItem>
                    );
                  }

                  // Always show last page (if more than 1 page)
                  if (totalPages > 1) {
                    pages.push(
                      <PaginationItem key={totalPages}>
                        <PaginationLink
                          onClick={() => handlePageChange(totalPages)}
                          isActive={currentPage === totalPages}
                          className="cursor-pointer"
                        >
                          {totalPages}
                        </PaginationLink>
                      </PaginationItem>
                    );
                  }

                  return pages;
                })()}

                {/* Next button */}
                <PaginationItem>
                  <PaginationNext
                    onClick={() => handlePageChange(currentPage + 1)}
                    className={currentPage >= pagination.pages ? "pointer-events-none opacity-50" : "cursor-pointer"}
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          )}
        </div>
      )}
    </div>
  );
}
