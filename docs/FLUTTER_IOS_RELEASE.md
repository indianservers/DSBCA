# iOS release preparation

This environment is Windows; Xcode, Apple signing and native iOS compilation/device acceptance are unavailable. **No archive or IPA was generated.**

Existing bundle IDs are preserved (User `com.dsbca.dsbcaUser`), display names are DSBCA/DSBCA Admin, deployment target is iOS 13.0, and plist syntax was parsed. ATS explicitly disallows arbitrary loads. User/Admin custom URL schemes are prepared separately. No camera, microphone, location or push permission is fabricated for inactive integrations.

Video player, file picker, share and secure-storage plugins are present in Flutter dependency locks and have iOS implementations; that is source/dependency inspection, not successful native linking. The owner must verify plugin deployment targets using CocoaPods/Xcode on macOS.

On an authorized macOS machine: install the pinned Flutter toolchain, resolve plugins, run analysis/tests, select the owner's team/bundle IDs, configure signing/provisioning and approved icons/launch screens, add verified associated domains if provided, and activate Firebase/APNs only with credentials/consent. Build an archive/export using the reviewed HTTPS API origin. Test on physical devices before TestFlight/App Store submission.

Review privacy manifests and App Store privacy answers against actual enabled SDK/data flows. Account deletion/export and legal text require an approved operational policy. No privacy-law certification or successful iOS release is claimed.
