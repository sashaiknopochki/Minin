export interface Language {
  code: string;
  en_name: string;
  original_name: string;
  display_order: number;
}

export interface LanguagesResponse {
  success: boolean;
  data: Language[];
  count: number;
}
