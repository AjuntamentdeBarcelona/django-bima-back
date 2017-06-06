/**
 * Geo-position Map
 * @constructor
 */

'use strict';
function GeopositionMap() {
  this.center = null;
  this.map = null;
  this.infoWindow = null;
}
GeopositionMap.prototype.init = function (element) {
    this.element = $(element);
    var self = this;
    var name = this.element.data('name');
    var address = this.element.data('address');
    var lat = parseFloat(this.element.data('latitude'));
    var lng = parseFloat(this.element.data('longitude'));

    var latLng = new google.maps.LatLng(lat, lng);
    this.map = new google.maps.Map(document.getElementById(this.element.attr('id')), {
        zoom: 13,
        center: latLng,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        scrollwheel: false
    });

    this.infoWindow = new google.maps.InfoWindow();

    var marker = new google.maps.Marker({position: latLng, map: self.map});
    var content = '<a href="#">' + name + '</a>';
    content += address ? '<br/>' + address : '';
    content += lat && lng ? '<br/>(' + lat + ', ' + lng + ')' : '';
    marker.content = content;
    marker.addListener('click', function (e) {
        self.infoWindow.setContent(this.content);
        self.infoWindow.setPosition(e.latLng);
        self.infoWindow.open(self.map, this);
    });

};
