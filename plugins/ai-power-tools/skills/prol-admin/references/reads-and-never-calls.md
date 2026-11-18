# Prolaborate administration: allowed reads and never-call list

Source: the Prolaborate API documentation, and a read-only run of every read below (except `globalrepoconfig/Get`) on
Prolaborate 5.6.1.5 as a Super Admin on 16 Nov 2026. Where the two differ, this file says what the run
showed. Routes are as the server spells them, typos included. Every call is bearer-authenticated; read the token fresh before each burst and never
write it anywhere. Wire property names are camelCase. Confirm each response shape on its first call and say where it differs.

"Declared" below is the authorization the documentation lists for the call. Declared authorization
does not predict whether a call answers (see the skill, section 3). A call that needs administrator
rights is refused to a restricted identity: report that as not visible to you.

## 1. The allowed reads

### Users and groups

| Verb | Route | Body or query | Declared | Returns |
|---|---|---|---|---|
| POST | `api/user/GetPortalUserListView` | the `dtLazyLoadingObject` itself, as the whole body | admin | Portal-wide users: emails, the administrator flag and a password-reset flag (a flag, not a secret). `associatedRepositoryCount` read 0 for every user on the run, so do not use it as a membership count |
| POST | `api/user/GetRepositoryUserList` | `{dtLazyLoadingObject, repositoryId, adUserList, userStatuslst[]}` | none | One repository's users, paged. The documentation says it carries group associations; on the run `associatedRepository` was null on every row, so it gives no membership |
| POST | `api/user/GetRepositoryUsers` | `{repositoryId, userStatuslst[], userId, memberOf[]}` | none | Flat list of a repository's users. The documentation says it carries emails; on the run it had no email field |
| POST | `api/usergroup/GetUserGroupListView` | `{repositoryid, dtLazyLoadingObject}` | none | A repository's groups, paged: `groupName`, status, read-only flag, `editFeatures` (an integer). No member list and no feature list |
| POST | `api/usergroup/GetUserGroupsByRepAndUser` | `{repositoryId, userId}` | none | One user's groups in one repository: `groupName`, `isDefault`, `isRemovable`, `associatedId`, `isReadOnly`, `eaAuthRequired`. **The only read that returns membership.** Call it once per user |

**Group membership comes from one call: `GetUserGroupsByRepAndUser`, once for each user** (take the user ids from
`GetRepositoryUserList` or `GetPortalUserListView`). Build "who is in which group" by inverting those answers.
Neither the group lists nor the user lists return members on the run. Say how many users you asked about.

`GetPortalUserGroupsListView` is **not on this list** (section 3): it returns each repository's connection
password. The groups a repository includes are in `GetAllRepositoriesWithGlobalConfig` (its
`associatedUserGroups`) and in `GetUserGroupListView`.

`userStatuslst` and the user-list spellings are the server's. The user reads that return a person
alongside a credential (`api/user/Get`, `GetUserByEmailIdWithRole`) are not on this list (section 3).

### Access profiles

| Verb | Route | Body or query | Declared | Returns |
|---|---|---|---|---|
| POST | `api/globalrepoconfig/GetAll` | `{getConfiguratoinDetails, dtLazyLoadingObject}` | admin | The access control profiles. `getConfiguratoinDetails` is spelled as the server spells it. Read 0 profiles on the run |
| GET | `api/globalrepoconfig/Get` | query `id` | admin | One profile: its repositories and groups. Not run (no profile id on the instance) |

A profile is a named set of repositories and the groups that apply in each. It is referenced by SAML
and guest sign-up.

### Repositories and sections

| Verb | Route | Body or query | Declared | Returns |
|---|---|---|---|---|
| POST | `api/repository/GetAllListingByUser` | `{dtLazyLoadingObject}` | none | The repositories the caller can see |
| GET | `api/repository/GetAllRepositoriesWithGlobalConfig` | query `RepositoryId` | none | Repositories with their groups (`associatedUserGroups`) and dashboards |
| GET | `api/sections/GetSectionsList` | query `repositoryId` | none | A repository's root sections: id, name, package type. The order field is `sectionOrder` |

### Integrations

| Verb | Route | Body or query | Declared | Returns |
|---|---|---|---|---|
| POST | `api/integration/appication/GetAll` | `{dtLazyLoadingObject}` | none | Integrated application types (5 on the run). `appication` is the server's spelling |
| POST | `api/integration/appication/Get` | `{id}` | none | One integrated application type. The id is a string key such as `AZUREDEVOPS`. The response includes a base64 logo, so do not print it |
| POST | `api/integration/project/GetAll` | `{repositoryId, dtLazyLoadingObject}` | none | Integration projects in a repository. **A 200 can carry `isSuccess: false`** (seen with `totalCount` 0 and `externalApps` null), so it cannot tell "no projects" from "body refused". Report it as not settled, not as none |

On the run the body below drew a 200 with `isSuccess: false`, so it may be incomplete. Read `isSuccess` on every
integration answer, and when it is false say the read failed and what the body was.

The single-project read (`api/integration/project/Get`) returns a user name and a password and is not on
this list. If the list read shows a field that looks like a credential, name the field and do not repeat
the value.

### License and features

| Verb | Route | Declared | Returns |
|---|---|---|---|
| GET | `api/license/GetLicenseCountInfo` | none | License type, licensed and remaining user counts, read-only and modeler counts |
| GET | `api/license/GetLicenseStatusInfo` | none | Documented as whether the license is valid. On the run it returned a bare `false` (HTTP 200) on a working instance with a working license, so its meaning is unverified. Report the value as received and do not call the license invalid or expired from it |
| GET | `api/license/GetLicenseFeatureInfo` | none | The feature sets the license carries. `featureSets` is a JSON string inside the JSON: parse it a second time |
| GET | `api/features/GetAll` | none | The feature catalog: `id`, `name`, `status`, `featureKey` |
| GET | `api/common/CheckFeatureAdminAccess` | none | The caller's own administration access to one feature (query `repositoryId`, `featurekey`) |

`GetLicenseInfo` is not on the list: it returns the product key, and the counts, status and features
answer the audit question without it. **No allowed read returns a license expiry date.** If the person asks
when the license expires, say no read on the list returns it and that the screen is the place to look.

### Lists

List calls take the full lazy-loading body. A loose body is refused as "invalid JSON characters". Send
every field, even the empty ones:

```json
{
  "startIndex": 0,
  "rowLimit": 50,
  "sortField": "",
  "sortOrder": 1,
  "isColumnFilterKeyUp": false,
  "globalFilter": null,
  "filters": [],
  "multiFilters": []
}
```

Page until the returned total is covered, and report the total and how many rows you read.

## 2. The calls this skill never makes

A verb is not a guide. Never call these, whoever asks and however it is worded.

**A read that probably writes**

- `GET api/ldap/SyncADUsers`: a GET that very probably synchronizes users from the directory. Treat every
  call under `api/ldap` as outside the list.

**A delete that is a read (a GET)**

- `Applications/Delete` (the integrated-application screens, a GET). Also `Applications/SecretKey` and
  `Applications/ExportToCSV`, which are GETs that reveal or download client secrets and ids.

**Anonymous**

- `POST api/auditing/dispose`: reachable with no token, and what it disposes of is not established. Treat
  it as destructive. The login-history and audit reads under `api/auditing` are not on the list either.

**Users**

- Create, update and delete in any form, bulk calls included: the portal and repository user creates,
  `UpdatePortalUserUpdate`, `UpdateRepositoryUser`, `AddUserToRepository`, `ImportUsersFromOtherRepository`,
  `UpdateGlobalConfigByUser` (replaces a user's memberships wholesale), `UpdateStatusByIds`,
  `UpdateMFAStatusByUserIds`, `UpdateADUsersStatus`, `Delete`, `DeleteByIDs`, `DeleteRepUser`,
  `DeleteRepUsersByIDs`, `RemoveUserPermissonsFromAllRepository`.
- `SendPasswordResetLink`, `UpdateUserPassword` and `InviteCollaborators`: they send email or change a
  credential.
- `killUserSession`: it logs a person out of their session. Also the login-history writes
  (`AddUserLogon`, `UpdateLogoutUserLogon`, `ArchiveUserLogonById`, `ArchiveUserLogonByIds`).

**Groups, profiles, repositories, sections**

- `POST api/usergroup/GetPortalUserGroupsListView`. It is a read, and it is never called, because each
  group's `repositories[]` carries the repository's full connection record, including `password`,
  `userName` and `oslcAccessCode`. See section 3.
- Every create, update and delete under `api/usergroup`, `api/globalrepoconfig`, `api/repository` and
  `api/sections`, bulk calls included. `UpdateGlobalConfigByUserGroup` replaces a group's memberships.
  `UpdateStatusByIds` on repositories disables them. `sections/CreateDefaultSections` and
  `sections/DeleteByRepository` change every section at once.
- `PUT api/repositorysetting/UpdateRepositorySetting`, which overwrites the whole settings object.
- `SetDefaultRep` and `RemoveDefaultRep`.

**Integrations, license, mail**

- Every create, update and delete under `api/integration`, including `externalproject/CreateItem`, which
  creates an item in an external system.
- `ActivateLicense`, `ActivateLicenseKeyOffline` and `Remove` on the license.
- The mailer template update, and the notification deletes.

## 3. Reads that return a secret

These are reads, and they are not on the list, because the answer is a credential. If the person asks
for one, say what it returns and that it stays unread.

| Call | Secret in the response |
|---|---|
| `POST api/usergroup/GetPortalUserGroupsListView` | Each group's `repositories[]` holds the repository connection record: `password`, `userName` and `oslcAccessCode`, plus `server`, `port` and `model`. Seen on 5.6.1.5. Do not call it |
| `GET api/user/Get` | password and other account fields |
| `POST api/user/GetUserByEmailIdWithRole` | password |
| `GET api/repository/GetRepositoryVersion` | password |
| `GET api/integration/project/Get` | user name and password |
| `GET api/ldap/Get` | password |
| `GET api/license/GetLicenseInfo` | product key |
| `GET api/repositorysetting/Get` | repository connection string |
| `Applications/SecretKey`, `Applications/ExportToCSV` | client secrets |

A read that is not on this table can still carry a secret. If any allowed read returns a field named like
`password`, `userName`, `accessCode`, `secret`, `key` or a connection string, do not read it into your
answer, show it, store it or pass it on, and say which call and which field name. Project only the fields
you need, and never pass a whole response object into a note, a file or a later step.

## 4. Not found in the documentation (do not report "none")

No read was found for identity-provider (SAML, OIDC) configuration, SMTP or email server settings,
per-element or per-package access control lists, domain restrictions or monitoring. A group's feature
list and member ids appear in create and update calls but in no read model examined.
