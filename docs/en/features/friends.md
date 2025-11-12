# Friend System

Connect with other maimai DX players, compare scores, and compete in rankings through JiETNG's friend system.

## Overview

The friend system allows you to:
- 👥 Add friends who use JiETNG
- 📊 Compare Best 50 rankings
- 🏆 View friend scores
- 🤝 Build your maimai community

:::warning Binding Required
You must [bind your SEGA ID](/guide/binding) to use friend features.
:::

## Friend List

### View Your Friends

**Command:**

```
friend list
friendlist
フレンドリスト
```

**What You See:**
- List of all your friends
- Their usernames/nicknames
- SEGA IDs
- Current rating (if available)
- Friend code for sharing

:::tip Empty List?
If your friend list is empty, you haven't added any friends yet! See the "Adding Friends" section below.
:::

## Adding Friends

There are multiple ways to add friends in JiETNG.

### Method 1: Direct Friend Request

**Command Format:**

```
add-friend [user_id]
friend request [user_id]
フレンド申請 [user_id]
```

**Example:**

```
add-friend U1234567890abcdef
friend request U9876543210fedcba
```

The recipient will receive a friend request notification.

:::tip Finding User IDs
User IDs are unique identifiers for LINE accounts. You can find them:
- From friend list exports
- By asking your friend directly
- From QR code sharing (Method 2)
:::

### Method 2: QR Code Sharing

JiETNG can generate QR codes that contain friend request links.

**How it works:**

1. User A generates a friend QR code (via special command or web interface)
2. User B scans the QR code with their phone camera or LINE
3. The QR code contains a link like:
   ```
   https://[domain]/linebot/add_friend?id=[user_id]
   ```
4. User B sends this link/QR image to the bot
5. Friend request is automatically sent!

:::tip QR Code Benefits
- No need to manually type user IDs
- Shareable in person (at arcades!)
- Can be posted in communities
- More convenient than copying IDs
:::

### Method 3: Friend Code

If implemented in your version, you can use short friend codes instead of full user IDs.

**Example:**

```
add-friend ABC-1234
```

Check with the bot documentation for your specific instance.

## Managing Friend Requests

### View Pending Requests

When you receive friend requests, you'll get notifications. Check them with:

```
friend requests
pending requests
```

### Accept a Friend Request

**Command Format:**

```
accept-request [request_id]
```

**Example:**

```
accept-request req_123456789
```

:::tip Request IDs
The request ID is shown in the friend request notification. It's different from the user ID - it's a unique identifier for that specific request.
:::

### Reject a Friend Request

**Command Format:**

```
reject-request [request_id]
```

**Example:**

```
reject-request req_123456789
```

The sender will NOT be notified that you rejected their request.

:::warning One-Time Decision
Once you accept or reject a request, you cannot undo it. To add the friend later (after rejection), they need to send a new request.
:::

## Comparing Scores

### Friend Best 50

View a friend's Best 50 chart to compare with your own.

**Command Format:**

```
friend-b50 [friend_code]
フレンドb50 [friend_code]
friend best50 [friend_code]
```

**Example:**

```
friend-b50 ABC123
```

:::warning Privacy Note
- This only works for users who have added you as a friend
- Both parties must have bound their SEGA IDs
- Some users may have privacy settings that restrict this
:::

### What's Shown

The friend B50 chart includes:
- Top 35 Standard charts
- Top 15 DX charts
- Total rating
- Chart details (score, rating contribution, difficulty)
- Similar layout to your own B50

### Use Cases

- **Competition**: See how you stack up
- **Goal Setting**: Find songs to improve on
- **Discovery**: Learn what songs your friends are playing
- **Community**: Share achievements together

## Friend System Technical Details

### How Friend Requests Work

1. **Sender** initiates request with `add-friend [user_id]`
2. **System** creates a friend request record with:
   - Unique request ID
   - Sender's user ID
   - Recipient's user ID
   - Timestamp
   - Status (pending)

3. **Recipient** receives notification
4. **Recipient** accepts or rejects using request ID
5. **System** updates both users' friend lists (if accepted)

### Privacy & Security

- ✅ Friend requests require explicit acceptance
- ✅ No auto-friending
- ✅ You control who can see your scores
- ✅ Can remove friends at any time
- ✅ Rejected requests don't notify sender

### Limitations

- **Max friends**: May have a limit (check with your bot instance)
- **Request expiration**: Old requests may expire after a period
- **Rate limiting**: Can't spam friend requests
- **Binding required**: Both users must have bound accounts

## Troubleshooting

### "User not found"

**Problem**: Can't send friend request - user not found

**Possible causes:**
- User ID is incorrect
- User hasn't bound their SEGA ID yet
- User doesn't use JiETNG
- Typo in the ID

**Solutions:**
- Double-check the user ID
- Ask your friend to verify they're bound with `get me`
- Try QR code method instead
- Make sure you're copying the full ID

### "Friend request already sent"

**Problem**: Can't send another request to the same user

**Explanation**: You've already sent a pending request. Wait for them to respond.

**Solution**:
- Wait for recipient to accept/reject
- Contact them directly to remind them
- Expired requests will clear after some time

### "Cannot view friend's B50"

**Problem**: `friend-b50` command doesn't work

**Possible causes:**
- Not actually friends yet (pending request)
- Friend hasn't bound their SEGA ID
- Friend's data hasn't been fetched from maimai NET
- Friend hasn't updated scores recently

**Solutions:**
- Verify you're friends with `friend list`
- Ask friend to run `maimai update`
- Check if friend is bound with their user ID
- Try again later

### Friend List is Empty After Adding

**Problem**: Accepted request but friend doesn't appear

**Possible causes:**
- Request was already expired
- System error during acceptance
- Cache needs refresh

**Solutions:**
- Try viewing list again
- Both users run `friend list` to verify
- Try removing and re-adding
- Report bug on [GitHub Issues](https://github.com/Matsuk1/JiETNG/issues)

## Best Practices

### For Better Friend Experience

1. **Update Regularly**: Run `maimai update` so friends can see your latest scores
2. **Clear Name**: Use a recognizable nickname in-game
3. **Active Friends**: Periodically review and clean up inactive friends
4. **Community**: Join Discord/groups to find more maimai friends
5. **QR Codes**: Use QR codes at arcades to quickly friend nearby players

### Building a Friend Network

- **Local Arcade Community**: Meet people at your local arcade
- **Online Communities**: Join maimai Discord servers, Reddit, etc.
- **Social Media**: Share your friend code on Twitter, forums
- **Tournaments**: Connect with players from events
- **Score Sharing**: Post your B50 and tag #maimai

## Friend Commands Quick Reference

| Command | Purpose |
|---------|---------|
| `friend list` | View all friends |
| `add-friend [id]` | Send friend request |
| `accept-request [req_id]` | Accept pending request |
| `reject-request [req_id]` | Reject pending request |
| `friend-b50 [code]` | View friend's Best 50 |

## Examples

### Adding a Friend at the Arcade

1. You meet someone playing maimai
2. They show you their QR code on their phone
3. You scan it with your phone camera
4. Send the link to JiETNG bot
5. Friend request sent automatically!
6. They accept later
7. Now you can compare B50s!

### Comparing Scores

```
# Check your own B50
b50

# Check friend's B50
friend-b50 XYZ789

# Compare ratings
friend list
```

### Cleaning Up Friends

```
# View all friends
friend list

# Note inactive friends
# (Currently no direct remove command - may need to unbind/rebind
# or contact support)
```

## Future Features

Potential friend system enhancements (not yet implemented):

- Friend leaderboards
- Friend activity feed
- Friend score comparisons on specific songs
- Friend challenges
- Friend groups/teams

Check the [GitHub repository](https://github.com/Matsuk1/JiETNG) for updates!

## Next Steps

- [Best 50 Feature](/features/b50) - Understand ranking charts
- [Account Binding](/guide/binding) - Required for friends
- [Support Page](/more/support) - Report issues
- [FAQ](/more/faq) - Common questions

---

**Quick Start:**

```bash
# 1. Add a friend
add-friend U1234567890abcdef

# 2. Accept requests (use request ID from notification)
accept-request req_123456789

# 3. View friends
friend list

# 4. Compare scores
friend-b50 ABC123
```
