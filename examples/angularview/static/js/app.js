angular.module('VoltronApp', [
    'VoltronApp.controllers',
    'VoltronApp.services'
])
.config(function($sceProvider) {
  $sceProvider.enabled(false);
});
