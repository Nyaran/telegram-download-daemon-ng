@manual @upload`l
Feature: Upload files
  AS a user
  I want to be able to send files directly to the channel
  THEN the bot should download the file

  Scenario Outline: Upload different kind of files
    Given an active bot channel
    When the user attach a file
      | client | <client> |
      | mode   | <mode>   |
      | type   | <type>   |
      | size   | <size>   |
    And the user waits until the file is downloaded
    Then file is present on the downloads folder

    @android
    Examples: Share
    Use share menu from Android
      | client  | mode  | type | size  |
      | Android | share | mp4  | 100MB |
      | Android | share | pdf  | 5MB   |
      | Android | share | zip  | 500MB |
      | Android | share | mkv  | 1.5GB |

    @android
    Examples: Media upload
    Use the media (image/video) upload dialog from Telegram client
      | mode    | type | size  |
      | Android | mp4  | 100MB |
      | Android | mkv  | 1.5GB |

    @android
    Examples: File upload
    Use the file (any kind) upload dialog from Telegram client
      | client  | mode | type | size  |
      | Android | file | mp4  | 100MB |
      | Android | file | pdf  | 5MB   |
      | Android | file | zip  | 500MB |
      | Android | file | mkv  | 1.5GB |

    @linux
    Examples: File upload
    Use the file (any kind) upload dialog from Telegram Desktop client
      | client  | mode | type | size  |
      | Desktop | file | mp4  | 100MB |
      | Desktop | file | pdf  | 5MB   |
      | Desktop | file | zip  | 500MB |
      | Desktop | file | mkv  | 1.5GB |
