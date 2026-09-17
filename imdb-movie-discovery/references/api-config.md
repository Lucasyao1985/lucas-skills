# IMDB GraphQL API Configuration

## API Endpoint
```
https://api.graphql.imdb.com/
```

## Authentication

All requests require the session cookie from a logged-in IMDB browser session. The `scripts/fetch_imdb.py` script reads cookies from the user's IMDB Cookie.txt export.

### Cookie Format (from browser export)
Generated from Chrome DevTools > Network > Copy as cURL. Import cookies via `scripts/fetch_imdb.py`.

## Required Headers
```
Content-Type: application/json
Origin: https://www.imdb.com
Referer: https://www.imdb.com/
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36
x-imdb-client-name: imdb-web-next
x-imdb-client-rid: <request-id-generate-fresh-each-call>
```

## Working Queries

### Trending Titles
```graphql
query {
  trendingTitles(limit: 10) {
    titles {
      id
      originalTitleText { text }
      titleType { id }
      releaseYear { year }
      ratingsSummary { aggregateRating voteCount }
      titleGenres { genres { genre { text } } }
      primaryImage { url }
    }
  }
}
```

### Title Details
```graphql
query {
  titles(ids: ["tt0111161"]) {
    id
    originalTitleText { text }
    titleType { id }
    releaseYear { year }
    ratingsSummary { aggregateRating voteCount }
    plot { plotText { plainText } }
    primaryImage { url }
    runtime { seconds }
    titleGenres { genres { genre { text } } }
    credits(first: 5) { edges { node { name { nameText { text } } } } }
    moreLikeThisTitles(first: 5) { edges { node { originalTitleText { text } releaseYear { year } ratingsSummary { aggregateRating } titleGenres { genres { genre { text } } } } } }
  }
}
```

### Similar Movies (More Like This)
```graphql
query {
  titles(ids: ["tt0111161"]) {
    moreLikeThisTitles(first: 10) {
      edges {
        node {
          id
          originalTitleText { text }
          titleType { id }
          releaseYear { year }
          ratingsSummary { aggregateRating voteCount }
          plot { plotText { plainText } }
          titleGenres { genres { genre { text } } }
          credits(first: 3) { edges { node { name { nameText { text } } } } }
          primaryImage { url }
          runtime { seconds }
        }
      }
    }
  }
}
```

### Search by Text
```graphql
query {
  mainSearch(options: {term: "Inception"}) {
    edges {
      node {
        ... on Title {
          id
          originalTitleText { text }
          releaseYear { year }
          ratingsSummary { aggregateRating }
          titleType { id }
        }
      }
    }
  }
}
```

## Known Field Constraints

| Object | Accessible Fields |
|--------|-------------------|
| Title | `id`, `originalTitleText`, `titleType`, `releaseYear`, `ratingsSummary`, `plot`, `primaryImage`, `runtime`, `titleGenres`, `credits`, `moreLikeThisTitles`, `canonicalUrl` |
| Genre | `text`, `id` (do NOT use `name`) |
| RatingsSummary | `aggregateRating`, `voteCount` |
| CreditConnection (credits) | `edges { node { name { nameText { text } } } }` — returns in billing order. No per-category filter publicly. |
| Runtime | `{ seconds }` |

## Rate Limiting & Usage

- Non-commercial personal use only per IMDB TOS
- Requests are blocked without valid session cookies (x-imdb-sessionid header)
- Add `x-amzn-sessionid: <session-id>` header when using existing cookies

## Direct Use

```bash
# Fetch trending movies
python scripts/fetch_imdb.py trending --limit 10

# Fetch title details
python scripts/fetch_imdb.py title --id tt0111161

# Fetch similar movies
python scripts/fetch_imdb.py similar --id tt0111161 --limit 5

# Fetch search results
python scripts/fetch_imdb.py search --query "Inception"
```
