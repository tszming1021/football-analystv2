export type OddsMap = Record<string, number>;

export type DeepMarket = {
  url: string;
  opening: number[];
  current: number[];
};

export type MatchItem = {
  match_num: string;
  fixture_page_id: string;
  league: string;
  home: string;
  away: string;
  kickoff: string;
  match_date: string;
  match_time: string;
  handicap: number | null;
  sale: {
    is_end: boolean;
    is_active: boolean;
    subactive: string;
    buy_end_time: string;
    display_style: string;
  };
  one_x_two: OddsMap;
  handicap_three_way: OddsMap;
  half_full: OddsMap;
  scores: OddsMap;
  total_exact: OddsMap;
  deep_market?: {
    ouzhi?: DeepMarket;
    yazhi?: DeepMarket;
    daxiao?: DeepMarket;
  };
};

export type MatchPayload = {
  fetched_at: string;
  source_url: string;
  source_http_date?: string;
  counts: {
    rows: number;
    on_sale: number;
    ended: number;
    included: number;
  };
  matches: MatchItem[];
  errors: Record<string, string>;
};

export type ImpliedProbability = {
  key: string;
  label: string;
  odds: number;
  probability: number;
  normalized: number;
};
