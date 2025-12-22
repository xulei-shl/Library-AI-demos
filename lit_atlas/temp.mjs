import VectorSource from 'ol/source/Vector.js';
import Feature from 'ol/Feature.js';
import Point from 'ol/geom/Point.js';

const source = new VectorSource();
const feature = new Feature({ geometry: new Point([0,0]) });
source.addFeature(feature);
const features = source.getFeatures();
console.log(features.length);
console.log(features[0] === feature);
