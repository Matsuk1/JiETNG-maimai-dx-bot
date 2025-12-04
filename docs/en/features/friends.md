# Friend System (Friend System)

Through JiETNG's friend system, you can connect with other 『maimai でらっくす』 players, compare scores, and compete in rankings.

## Overview

The friend system allows you to:
- 👥 Add other JiETNG users as friends
- 🏆 View friends' scores
- 🤝 Build your maimai community

:::warning Binding Required
You must [bind your SEGA ID](/en/guide/binding) before using friend features.
:::

## Friend List

### View Friend List

**Command:**

```
friend list
friendlist
フレンドリスト
```

**Display Content:**
- List of all friends
- Their username or nickname
- Current Rating

:::tip Empty List?
If your friend list is empty, it means you haven't added any friends yet! Please refer to the "Adding Friends" section below.
:::

## Adding Friends

In JiETNG, there are multiple ways to add friends.

### Method 1: Direct Friend Request

**Command Format:**

```
add-friend [user_id]
friend request [user_id]
フレンド申請 [user_id]
```

**Examples:**

```
add-friend U1234567890abcdef
friend request U9876543210fedcba
```

The recipient will receive a friend request notification.

:::tip How to Find User ID
User ID is the unique identifier for a LINE account and can be obtained by:
- Asking your friend directly
- Scanning your friend's QR code (see Method 2)
:::

### Method 2: QR Code Sharing

JiETNG can generate QR codes that contain friend invitation links.

**Process Description:**

1. User A generates a friend QR code (via command or web interface)
2. User B scans the QR code with their phone camera or LINE
3. The QR code contains a link like:
   ```
   https://[domain]/linebot/add_friend?id=[user_id]
   ```
4. User B sends this link or QR image to the bot
5. Friend request is sent automatically!

:::tip Benefits of QR Codes
- No need to manually enter ID
- Can add friends offline (e.g., at arcades)
- Can share in communities
- More convenient than copying ID
:::

## Managing Friend Requests

### View Pending Requests

When you receive a friend request, you'll get a notification. You can view them with:

```
friend requests
pending requests
```

### Accept Friend Request

**Command Format:**

```
accept-friend-request [request_id]
```

**Example:**

```
accept-friend-request req_123456789
```

:::tip About Request ID
Request ID is displayed in the friend request notification. It's different from user ID and is the unique identifier for that request.
:::

### Reject Friend Request

**Command Format:**

```
reject-friend-request [request_id]
```

**Example:**

```
reject-friend-request req_123456789
```

The sender will not be notified that you rejected the request.

:::warning Note
Once you accept or reject a request, the action is irreversible. If you want to add that friend again, they need to send a new request.
:::

## Comparing Scores

### View Scores as Friend

You can view scores as a friend to compare with your own.

**Command Format:**

```
friend-b50 [friend_code]
```

**Example:**

```
friend-b50 ABC123
```

:::warning Privacy Note
- Only works for users who have added you as a friend
- Both parties must have bound their SEGA ID
:::


### Privacy & Security

- ✅ All friend requests require explicit consent
- ✅ No auto-friending
- ✅ Rejecting requests doesn't notify the sender

### Limitations

- **Request Expiration**: Old requests may expire after a certain period
- **Rate Limiting**: Prevents spam friend requests
- **Binding Requirement**: Both parties must have bound accounts

## Troubleshooting

### "User Not Found"

**Problem:** Cannot send friend request.

**Possible Causes:**
- Incorrect user ID
- Recipient hasn't bound SEGA ID
- Recipient doesn't use JiETNG
- ID spelling error

**Solutions:**
- Check if ID is correct
- Have the recipient verify binding status with `get me`
- Try using QR code method instead
- Ensure you copied the complete ID

---

### "Request Already Sent"

**Problem:** Already sent a request, cannot send again.

**Reason:** The recipient hasn't processed the previous request yet.

**Solutions:**
- Wait for them to accept or reject
- You can remind them to process the request
- Can resend after expiration

---


### Friend List Empty After Adding

**Problem:** Accepted request but friend doesn't appear.

**Possible Causes:**
- Request has expired
- System error during acceptance
- Cache hasn't refreshed yet

**Solutions:**
- View list again
- Both parties execute `friend list`
- Try adding again
- If still abnormal, report at [GitHub Issues](https://github.com/Matsuk1/JiETNG/issues)

## Usage Suggestions

### Tips to Improve Friend Experience

1. **Update Scores Regularly**: Use `maimai update` to let friends see your latest scores
2. **Use Clear Nickname**: Make it easy for friends to recognize you
3. **Clean Up Inactive Friends**: Keep your list organized
4. **Join Communities**: Join Discord or discussion groups
5. **Use QR Codes**: Quickly add friends at arcades

### Ways to Build Friend Network

- **Arcade Offline**: Add regular players you meet
- **Online Communities**: Join maimai forums, Discord groups, etc.
- **Social Media**: Share your friend code on Twitter or forums
- **Competitions**: Connect with participants
- **Score Sharing**: Post your B50 with #maimai tag

## Friend Commands Quick Reference

| Command | Purpose |
|------|------|
| `friend list` | View friend list |
| `add-friend [id]` | Send friend request |
| `accept-friend-request [req_id]` | Accept request |
| `reject-friend-request [req_id]` | Reject request |
| `friend-b50 [code]` | View friend Best 50 |

## Usage Examples

### Adding Friends at the Arcade

1. You meet a player who's playing
2. They show their QR code on their phone
3. You scan the QR code with your phone
4. Send the generated link to JiETNG bot
5. System automatically sends friend request
6. They accept later
7. Now you can view each other's B50!

### Score Comparison

```
# View your own B50
b50

# View scores as friend
friend-b50 XYZ789

# View friend list
friend list
```

## Future Planned Features

Possible future additions to the friend system:

- Friend leaderboards
- Friend activity feed
- Score comparison for specific songs
- Friend challenge system
- Friend groups / teams

Follow the [GitHub project page](https://github.com/Matsuk1/JiETNG) for latest updates.

## Next Steps

- [Account Binding Guide](/en/guide/binding) — Prerequisite for friend features
- [Support Page](/en/more/support) — Report issues
- [FAQ](/en/more/faq)

---

**Quick Start:**

```bash
# 1. Add friend
add-friend U1234567890abcdef

# 2. Accept friend request
accept-friend-request req_123456789

# 3. View friends
friend list

# 4. View scores as friend
friend-b50 ABC123
```
