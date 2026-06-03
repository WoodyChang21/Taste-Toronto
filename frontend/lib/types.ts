export interface Intent {
  occasion: string | null;
  group_size: number | null;
  budget: "$" | "$$" | "$$$" | "$$$$" | null;
  neighborhood: string | null;
  vibe: string[];
  cuisine: string[];
  is_complete: boolean;
  needs_followup: boolean;
  followup_question: string | null;
  missing_fields: string[];
}

export interface ScoredRestaurant {
  id: string;
  name: string;
  address: string;
  neighborhood: string;
  cuisine: string;
  price_range: string;
  rating: number;
  review_count: number;
  phone: string | null;
  website: string | null;
  reservation_url: string | null;
  noise_level: "quiet" | "moderate" | "lively" | null;
  parking: boolean | null;
  semantic_tags: string[];
  occasion_scores: Record<string, number>;
  description: string;
  latitude: number | null;
  longitude: number | null;
  google_maps_url: string | null;
}

export interface ChatResponse {
  session_id: string;
  message: string;
  restaurants: ScoredRestaurant[];
  intent: Intent | null;
  needs_followup: boolean;
}

export interface UIMessage {
  role: "user" | "assistant";
  content: string;
  restaurants?: ScoredRestaurant[];
  needs_followup?: boolean;
}
