from pathlib import Path

p = Path("work/src/CRCarplayWindow.mm")
s = p.read_text()
needle = "    self.splitScreenEnabled = YES;

    // Re-assert both hosted scenes as active after split creation.
    [self forceHostedSceneForeground:self.appViewController];
    [self forceHostedSceneForeground:self.appViewController2];
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.8 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
        [self forceHostedSceneForeground:self.appViewController];
        [self forceHostedSceneForeground:self.appViewController2];
    });"

controls = r'''

    // DuoDash Lite controls. Keep controls persistent while either hosted app changes.
    if ([self.dockView viewWithTag:9101] == nil) {
        UIButton *app1Toggle = [UIButton buttonWithType:UIButtonTypeSystem];
        app1Toggle.tag = 9101;
        app1Toggle.frame = CGRectMake(8, 8, 42, 42);
        [app1Toggle setTitle:@"L" forState:UIControlStateNormal];
        [app1Toggle addTarget:self action:@selector(toggleFirstSplitApp) forControlEvents:UIControlEventTouchUpInside];
        [self.dockView addSubview:app1Toggle];
    }

    if ([self.dockView viewWithTag:9102] == nil) {
        UIButton *app2Toggle = [UIButton buttonWithType:UIButtonTypeSystem];
        app2Toggle.tag = 9102;
        app2Toggle.frame = CGRectMake(8, 56, 42, 42);
        [app2Toggle setTitle:@"R" forState:UIControlStateNormal];
        [app2Toggle addTarget:self action:@selector(toggleSecondSplitApp) forControlEvents:UIControlEventTouchUpInside];
        [self.dockView addSubview:app2Toggle];
    }
'''

if needle not in s:
    raise SystemExit("split marker not found")
s = s.replace(needle, needle + controls, 1)

methods = r'''
- (void)forceHostedSceneForeground:(id)viewController
{
    if (!viewController) return;

    // Some apps (notably Google Maps on iOS 14) stop network-backed rendering
    // when SpringBoard still considers their hosted scene backgrounded/occluded.
    objcInvoke_1(viewController, @"setIgnoresOcclusions:", 1);

    id sceneHandle = objcInvoke(viewController, @"sceneHandle");
    if (!sceneHandle) return;

    id appScene = objcInvoke(sceneHandle, @"sceneIfExists");
    if (!appScene) return;

    id sceneSettings = objcInvoke(appScene, @"mutableSettings");
    if (!sceneSettings) return;

    objcInvoke_1(sceneSettings, @"setBackgrounded:", 0);
    objcInvoke_1(sceneSettings, @"setForeground:", 1);

    ((void (*)(id, SEL, id, id, void *))objc_msgSend)(
        appScene,
        NSSelectorFromString(@"updateSettings:withTransitionContext:completion:"),
        sceneSettings,
        nil,
        0
    );

    id animationFactory = objcInvoke(objc_getClass("SBApplicationSceneView"), @"defaultDisplayModeAnimationFactory");
    id appView = objcInvoke(viewController, @"appView");
    if (appView) {
        objcInvoke_3(appView, @"setDisplayMode:animationFactory:completion:", 4, animationFactory, 0);
    }
}

- (void)layoutVisibleSplitApps
{
    if (!self.splitScreenEnabled || !self.appViewController2 || !self.appContainerView2) return;

    [self forceHostedSceneForeground:self.appViewController];
    [self forceHostedSceneForeground:self.appViewController2];

    BOOL a = !self.appContainerView.hidden;
    BOOL b = !self.appContainerView2.hidden;

    if (!a && !b) {
        self.appContainerView.hidden = NO;
        a = YES;
    }

    CGRect r = self.rootWindow.bounds;
    CGFloat d = self.isFullscreen ? 0 : CARPLAY_DOCK_WIDTH;
    CGFloat x = [self shouldUseRightHandDock] ? 0 : d;
    CGFloat w = r.size.width - d;

    if (a && b) {
        CGFloat g = 2.0f;
        CGFloat l = (w - g) / 2.0f;
        self.appContainerView.frame = CGRectMake(x, 0, l, r.size.height);
        self.appContainerView2.frame = CGRectMake(x + l + g, 0, w - g - l, r.size.height);
    } else {
        UIView *v = a ? self.appContainerView : self.appContainerView2;
        v.frame = CGRectMake(x, 0, w, r.size.height);
    }
}

- (void)toggleFirstSplitApp
{
    if (!self.splitScreenEnabled || !self.appViewController2) return;

    self.appContainerView.hidden = !self.appContainerView.hidden;
    if (self.appContainerView.hidden && self.appContainerView2.hidden) {
        self.appContainerView2.hidden = NO;
    }
    [self layoutVisibleSplitApps];
}

- (void)toggleSecondSplitApp
{
    if (!self.splitScreenEnabled || !self.appViewController2) return;

    self.appContainerView2.hidden = !self.appContainerView2.hidden;
    if (self.appContainerView.hidden && self.appContainerView2.hidden) {
        self.appContainerView.hidden = NO;
    }
    [self layoutVisibleSplitApps];
}

// DuoDash Lite: when one slot is hidden/full-screen, selecting another app replaces
// the hidden slot and keeps the visible app full-screen.
- (void)selectAppForSplitWithBundleIdentifier:(NSString *)identifier
{
    BOOL keepSingleVisible = NO;

    if (self.splitScreenEnabled && self.appContainerView2) {
        // If App 1 is hidden while App 2 is full-screen, swap the logical
        // slots first. setupSecondApp... can then replace the hidden slot.
        if (self.appContainerView.hidden && !self.appContainerView2.hidden) {
            UIView *container = self.appContainerView;
            self.appContainerView = self.appContainerView2;
            self.appContainerView2 = container;

            id controller = self.appViewController;
            self.appViewController = self.appViewController2;
            self.appViewController2 = controller;

            id monitor = self.sceneMonitor;
            self.sceneMonitor = self.sceneMonitor2;
            self.sceneMonitor2 = monitor;

            id app = self.application;
            self.application = self.application2;
            self.application2 = app;
        }

        keepSingleVisible = (!self.appContainerView.hidden && self.appContainerView2.hidden);
    }

    [self setupSecondAppWithBundleIdentifier:identifier];

    if (keepSingleVisible && self.appContainerView2) {
        self.appContainerView.hidden = NO;
        self.appContainerView2.hidden = YES;
        [self layoutVisibleSplitApps];
    }
}

'''

i = s.rfind("@end")
if i < 0:
    raise SystemExit("@end not found")

p.write_text(s[:i] + methods + s[i:])
