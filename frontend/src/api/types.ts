export interface DatasetItem {
  name: string;
  path: string;
  format: string;
  row_count: number;
}

export interface FilterOptionsResponse {
  contests: string[];
  departments: string[];
  municipalities: string[];
  parties: string[];
  candidates: string[];
}

export interface CandidateIdentity {
  name: string;
  party?: string | null;
  contest?: string | null;
}

export interface CandidateScope {
  dataset: string;
  department?: string | null;
  municipality?: string | null;
  party?: string | null;
}

export interface CandidateStats {
  total_votes: number;
  total_tables: number;
  tables_with_votes: number;
  tables_without_votes: number;
  coverage_pct: number;
  avg_participation: number;
  municipalities_with_votes: number;
  winning_tables: number;
  narrow_loss_tables: number;
  narrow_loss_margin_threshold: number;
}

export interface ZoneSummary {
  department_name?: string | null;
  municipality_name?: string | null;
  zone_code?: string | null;
  zone_label: string;
  votes: number;
  total_votes: number;
  participation: number;
  tables: number;
  places: number;
  winning_tables: number;
}

export interface TableSummary {
  table_key: string;
  department_name?: string | null;
  municipality_name?: string | null;
  zone_code?: string | null;
  polling_place_name?: string | null;
  table_code?: string | null;
  votes: number;
  total_table_votes: number;
  pct: number;
  margin: number;
  rival_name?: string | null;
  rival_votes?: number | null;
  winner_label?: string | null;
  winner_votes?: number | null;
}

export interface CandidateSummaryResponse {
  candidate: CandidateIdentity;
  scope: CandidateScope;
  stats: CandidateStats;
  top_zones: ZoneSummary[];
  top_tables: TableSummary[];
  tables_won: TableSummary[];
  tables_lost_narrow: TableSummary[];
}

export interface CompetitiveRival {
  rival_name: string;
  rival_party?: string | null;
  rival_votes: number;
  candidate_votes: number;
  tables_candidate_wins: number;
  tables_rival_wins: number;
  tables_tied: number;
  avg_rival_participation: number;
  avg_candidate_participation: number;
}

export interface HeadToHeadPoint {
  table_key: string;
  municipality_name?: string | null;
  zone_code?: string | null;
  polling_place_code?: string | null;
  polling_place_name?: string | null;
  table_code?: string | null;
  candidate_votes: number;
  rival_votes: number;
  vote_difference: number;
  winner_name: string;
  candidate_pct: number;
  rival_pct: number;
  rival_name: string;
}

export interface CompetitiveResponse {
  candidate: CandidateIdentity;
  scope: CandidateScope;
  total_candidate_tables: number;
  rivals: CompetitiveRival[];
  head_to_head: HeadToHeadPoint[];
}

export interface MunicipalHighlight {
  municipality_name?: string | null;
  department_name?: string | null;
  value: number;
}

export interface MunicipalSummary {
  total_municipalities: number;
  total_municipalities_available: number;
  best_municipality?: MunicipalHighlight | null;
  most_efficient_municipality?: MunicipalHighlight | null;
}

export interface MunicipalRow {
  municipality_name: string;
  department_name?: string | null;
  total_votes: number;
  total_tables: number;
  tables_with_votes: number;
  coverage_pct: number;
  efficiency: number;
  rank_in_department: number;
  top_rival_name?: string | null;
  top_rival_votes: number;
}

export interface MunicipalComparisonResponse {
  candidate: CandidateIdentity;
  scope: CandidateScope;
  summary: MunicipalSummary;
  municipalities: MunicipalRow[];
}

export type DrilldownLevel = "zone" | "polling_place" | "table";

export interface DrilldownContext {
  municipality?: string | null;
  zone_code?: string | null;
  polling_place_code?: string | null;
  polling_place_name?: string | null;
}

export interface ZoneDrilldownItem {
  zone_code?: string | null;
  candidate_votes: number;
  total_votes: number;
  candidate_pct: number;
  tables_total: number;
  tables_with_votes: number;
  places_count: number;
  rank_in_zone: number;
  zone_winner?: string | null;
  zone_winner_votes: number;
}

export interface PollingPlaceDrilldownItem {
  polling_place_code?: string | null;
  polling_place_name?: string | null;
  candidate_votes: number;
  total_votes: number;
  candidate_pct: number;
  tables_total: number;
  tables_with_votes: number;
  rank_in_place: number;
  place_winner?: string | null;
  place_winner_votes: number;
}

export interface TableTopRival {
  name: string;
  votes: number;
  pct: number;
}

export interface TableDrilldownItem {
  table_code?: string | null;
  candidate_votes: number;
  total_votes: number;
  candidate_pct: number;
  rank_in_table: number;
  table_winner?: string | null;
  table_winner_votes: number;
  margin_vs_second: number;
  top_rivals: TableTopRival[];
}

export interface ZoneDrilldownResponse {
  level: "zone";
  context: DrilldownContext;
  items: ZoneDrilldownItem[];
}

export interface PollingPlaceDrilldownResponse {
  level: "polling_place";
  context: DrilldownContext;
  items: PollingPlaceDrilldownItem[];
}

export interface TableDrilldownResponse {
  level: "table";
  context: DrilldownContext;
  items: TableDrilldownItem[];
}

export type CandidateDrilldownResponse =
  | ZoneDrilldownResponse
  | PollingPlaceDrilldownResponse
  | TableDrilldownResponse;

export interface FilterState {
  dataset: string;
  contest: string;
  department: string;
  municipality: string;
  party: string;
  candidate: string;
}

export type MunicipalSort = "votes" | "efficiency" | "coverage";
