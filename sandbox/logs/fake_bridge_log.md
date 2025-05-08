# Mock Bridge Fault Log for Timestamp Normalization Test

## Log Entries
2024-07-26 10:00:00,123 - INFO - Node A bridge connection established. Expected UTC: 2024-07-26T10:00:00.123Z
2024-07-26T10:00:05.456Z - ERROR - Node B fault: Connection timeout. Expected UTC: 2024-07-26T10:00:05.456Z
2024-07-26 02:00:10,789 - WARN - Node C clock drift suspected (Log time is PST). Expected UTC: 2024-07-26T10:00:10.789Z
2024-07-26T10:00:15.999+00:00 - INFO - Node D health check OK. Expected UTC: 2024-07-26T10:00:15.999Z
2024-07-26 10:00:20,000 - ERROR - Node A bridge fault: Packet loss detected. Expected UTC: 2024-07-26T10:00:20.000Z
Invalid timestamp format - DEBUG - Low level system message. Expected UTC: N/A (should be skipped)
2024-07-26T03:00:25.111-07:00 - INFO - Node C status update (Log time is PDT). Expected UTC: 2024-07-26T10:00:25.111Z
2024-07-26 10:00:30,555 - INFO - Node B recovered. Expected UTC: 2024-07-26T10:00:30.555Z

## Notes
- Line 3 & 7 have timestamps recorded in US/Pacific time (PST/PDT, UTC-8/UTC-7) but lack timezone indicators in the standard format. This tests the normalization assumption.
- Line 6 has an invalid format to test skipping/error handling.
- 'Expected UTC' is added for test validation reference. 