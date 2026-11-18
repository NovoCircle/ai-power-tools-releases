# Reading Prolaborate reviews: calls, bodies and traps

Source: the Prolaborate API documentation for the review controller (route `api/Review`, capital R,
copied exactly), a walk of the Reviews page on 5.6.1.40 as a Super Admin, and read-only runs on 5.6.1.5 as
a Super Admin on 16 Nov 2026 against one test review (one contributor, two items, no discussion). Measured
there: the list, the count, `GetReviewById`, `GetReviewSummaryInfo`, `GetReviewerQuickSummary`,
`GetReviewReport` and `GetCollaborations`. Request shapes for the other calls are from the documentation.
Run the first call of a session, compare the response with what is written here, and say where they differ.

Every call is bearer-authenticated: send `Authorization: Bearer <token>`, read the token fresh before
each burst of calls, and never write it anywhere. Wire property names are camelCase.

## 1. The reads

| Verb | Route | Body or query | Returns |
|---|---|---|---|
| POST | `api/Review/GetReviewsList` | `repositoryId`, `reviewFilters`, `dtLazyLoadingObject` (below) | `{"reviewsList": [...]}`: the page of reviews. Rows carry `reviewStartDate`, `reviewEndDate` (ISO date-times), `daysLeft`, `createdDate`, `modifiedDate`, and `status` as a lower-case string (`active`) |
| POST | `api/Review/GetUserReviewsCount` | the same body | `{"reviewsCounter", "archivedReviewsCount"}`: the count for the list, a separate round trip |
| GET | `api/Review/GetReviewById` | query `reviewProcesseId` (extra `e`) | One review: `id`, `name`, `notes`, the review and approval dates as `dd-MM-yyyy` strings, `repositoryId`, `status`, `workFlow`, `externalUsersInvite`, `enableShare`, `emailNotification`, `author`, `loggedInUserInfo`, `daysLeft`, `isReviewActionsEnabled`. No percent complete, no counts |
| POST | `api/Review/GetReviewElementsList` | review id, repository id, `dtLazyLoadingObject` | The items, with review-wide counts and discussion counts |
| POST | `api/Review/GetReviewElementsCount` | the same body | The count for the items |
| POST | `api/Review/GetReviewItemsTree` | review id, repository id, optionally `elementGuid` | Tree nodes, the children of `elementGuid` when set |
| GET | `api/Review/GetElementContributorsStatus` | query `reviewProcessId` (no extra `e`) and the item | Who reviewed or approved that item, review-wide |
| POST | `api/Review/GetReviewContributorsList` | review id | Approvers and reviewers with a status |
| POST | `api/Review/GetApproverQuickSummary`, `GetReviewerQuickSummary`, `GetModeratorQuickSummary` | review id | Role roll-ups. `GetReviewerQuickSummary` with `{reviewProcessId, repositoryId}` returned `reviewDoneCount` and `reviewPendingCount` |
| GET | `api/Review/GetReviewReport` | query `reviewProcesseId` (extra `e`) | The only read from this controller that returns discussion text. Wrapped as `{getReviewReport: {...}}`, with open and closed discussion counts |
| POST | `api/reports/GetReviewSummaryInfo` | `{reviewProcessId, repositoryId}` | The numbers behind the Reviews List widget: `reviewedCount`, `reviewsElementsCount`, `completedReviewerCount`, `reviewerCount`, `reviewPeriod`, `daysLeft`. No dates. User context |
| POST | `api/collaboration/GetCollaborations` | filtered by `reviewId` (body below) | Discussions: `{collaborations: [...], enableEACollaboration, loggedInUserId, ...}` |

`GetReviewSummaryInfo` and `GetReviewerQuickSummary` took `{reviewProcessId, repositoryId}` as written. The
list also accepted `isIncludeArchivedReviews: true` as a boolean.

The `GetCollaborations` body that was accepted (a guessed body was refused as "invalid JSON characters"):

```json
{
  "repositoryId": "<id from the preflight>",
  "elementGuids": [],
  "collaborationFilters": { "reviewId": "<review id>", "ProlStatus": [] },
  "isAccessCheckRequired": false,
  "limit": 50,
  "offset": 0,
  "userFilter": false
}
```

The page's own count call uses the same filter object with `"ProlStatus": ["open"]`.

The list request body:

```json
{
  "repositoryId": "<id from the preflight>",
  "reviewFilters": {
    "status": [],
    "elementId": null,
    "isMyReviews": false,
    "isIncludeArchivedReviews": false,
    "isReviewer": 0,
    "isModerator": 0,
    "isApprover": 0
  },
  "dtLazyLoadingObject": {
    "startIndex": 0,
    "rowLimit": 50,
    "sortField": "",
    "sortOrder": 1,
    "isColumnFilterKeyUp": false,
    "globalFilter": null,
    "filters": [],
    "multiFilters": []
  }
}
```

**The role flags `isReviewer`, `isModerator` and `isApprover` are the integer `0`, not `false`, on
`GetReviewsList`.** With `false` the server answers 400 "Request body contains invalid JSON characters"
(seen on 5.6.1.5). `GetUserReviewsCount` accepted booleans on the same body, so the two calls differ: send
the same integer flags to both, and if either is refused, say which call and what it said. The Reviews page
itself sends `elementId: ""`, role flags `0`, no `isIncludeArchivedReviews`, and a `dtLazyLoadingObject` that
also carries a `multiSort` field. The body above, with flags `0`, was accepted (200).

Send every field of `dtLazyLoadingObject`, even the empty ones: a loose body is refused as "invalid JSON
characters". An empty `status` list returned the one Active review on the run, so it did not filter that review out.
Whether it also returns Closed reviews is unchecked (only an Active review existed): confirm against the
page's own count. The state string received was `active`, lower case, while the page shows "Active". The
exact value strings the `status` filter accepts are not recorded: take them from a response before
filtering on one.

## 2. Wire traps

1. **The review id is spelled two ways.** `reviewProcesseId` (extra `e`) on `GetReviewById`,
   `DeleteReviewById`, `GetReviewDiscussionsCountByStatus`, `GetReviewDiscussionsCountByPriority`,
   `GetReviewUsersList`, `GetUsersListForInviteReview` and `GetReviewReport`. `reviewProcessId` on
   `GetReviewNameById`, `GetReviewElementsByReviewId`, `GetReviewElementInfo`,
   `GetReviewElementStereotypes`, `GetReviewDiagramsAuthor` and `GetElementContributorsStatus`. Use the
   exact spelling per endpoint. A wrong spelling does not always fail: check the response is the
   review you asked for.
2. **Per-user status flags are not aggregates.** `isReviewDone`, `isApproved` and `isRejected` on an
   item describe the calling user. For review-wide status use `reviewDoneUsersCount`,
   `approvedUsersCount`, `rejectedUsersCount`, or `GetElementContributorsStatus`.
3. **Two types share the name `ReviewContributor`.** The request shape (`isReviewer`, `isApprover`,
   `isModerator`) and the response shape (`role`, `userReviewStatus`) are not interchangeable.
4. **Items have two identifiers.** `reviewElementId` for status and action calls, `guid` for
   `elementGuids` and `GetReviewElementInfo`. They are different values.
5. **`status` on a review is a free string**, not an enum.
6. **Booleans are integers**: `workFlow`, `externalUsersInvite`, `enableShare`, `emailNotification`,
   `reviewDone`.
7. **Dates are formatted differently by call.** `GetReviewById` gives `dd-MM-yyyy` strings (`16-11-2026`).
   The list and the report give ISO date-times (`2026-11-16T00:00:00`). `GetReviewSummaryInfo` gives no
   dates. Convert before subtracting. `daysLeft` counts inclusively (an end date three days away read
   "4 Days left"), so compute time used from the dates, not from `daysLeft`. Percent complete is not on
   `GetReviewById`: use `reviewedCount` over `reviewsElementsCount` from `GetReviewSummaryInfo`.
8. **Typos are part of the wire contract**: `reviwedItems`, `openDisscussionObj`,
   `closeDisscussionObj`, `discussionLable`, `replayDiscussion`, `reviewelementStatus`. Read them as
   spelled.
9. **Swapped doc comments.** On the items-tree request model the notes describe the repository id as the
   review id and the other way round. Trust the field names, not the prose.
10. **A `200` can carry a failure.** `isSuccess: false` inside a success response is a normal failure.
11. **Personal data.** Some user lists return email addresses and the administrator flag. They are not
    on the list of calls this skill makes.

## 3. The calls this skill never makes

Writes: `AddReview`, `UpdateReview`, `UpdateReviewsStatus`, `DeleteReviewById`, `AddReviewApproval`,
`AddReviewDoneStatus`, `UpdateAllReviewElementsStatus`, `InviteReviewCollaborators`. They act as the
caller, so a call here is an approval, a status change or an email from a real person. The status write
accepts only `archive`, `closed` and `disabled`, and none of those can be taken back quietly.

**Anonymous scheduler jobs, never called:**

- `POST api/Review/UpdateReviewStatusByScheduler`: takes no body and updates review statuses across
  the whole system.
- `POST api/Review/NotifyExpiryingReviewToUsers`: takes no body and sends email and push notifications.

Both are reachable without a token, which is the reason they are dangerous: no identity is attached and
nothing limits them to the repository you are looking at. They are not exercised by this skill, not even
to see whether they answer.

Rate-limited: `GetReviewContributorDetails` is the only review action carrying the API limit, and
`api/collaboration/Count` carries it too. Avoid both, and never call either inside a loop.

## 4. Notes for reading the Reviews page

- A review card shows the title, the author, the state, and for a review the viewer takes part in,
  "My status" and a days-left countdown. A Closed review showed neither.
- The page's filter panel lists the states Active, Incomplete, Not yet started, Closed and Hold, a
  switch for archived reviews, and an All Reviews or My Reviews choice.
- A review that the list shows, even under My Reviews, can answer "Access Restricted" on its detail
  page. The list is not permission-scoped; the detail page is.
- Opening a review's detail page makes the page call `api/collaboration/Count` itself. That is fine for
  one review, but a loop that opens many detail pages would hit the rate-limited call.
- The Reviews List widget has no configuration of its own. It borrows nothing from the page's filters.
